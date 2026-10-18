# DRAFT-24651: strip-invalid-codesign-and-selfsign

OHOS conan 包树内 .codesign 失效的 ELF 无法执行/加载（exec EPERM 126 / dlopen EACCES 13）→ 移除失效签名段 + 自签

## 基本信息
- **严重度**: 3（🔴 blocking）
- **类别**: ohos, platform, conan, codesign, selinux
- **作者**: gcw_Pp8UzTBn <2280277721@qq.com>
- **来源**: rofi/2.0.0 OHOS 适配（Wayland 后端），2026-10-16，3 处实证
- **状态**: 草稿（待主编审核 promote）

## 错误特征
```
.conan2/p/<pkg><hash>/p/bin/<tool>    →  Operation not permitted   (exit 126 / EPERM)
dlopen(<pkg>/lib/lib<name>.so)        →  dlerror errno=13          (EACCES)
<同一二进制在构建目录/$HOME>          →  正常运行
llvm-readelf -S <elf> | grep codesign →  .codesign 段存在但签名失效
```

## 根因分析
1. OHOS 真机内核对**包树路径**（`.conan2/p/...` conan 缓存包目录）下 ELF 的 execve/dlopen 强制校验 `.codesign` 段有效性。
2. ohpcd 制品仓下载的预编译包内二进制可能携带**失效签名**（陈旧签名/错配/占位）。
3. 签名校验的强制范围是**路径依赖**的（实测对照）：同一 ELF 在构建目录/$HOME 可执行，在包树内 126/EACCES →
   "构建阶段通过、包树执行失败"不是环境抖动，是本问题类的正常表现。
4. 对照实验：ohpcd wayland/1.22.0 同包内 `libwayland-client.so.0.22.0`（签名有效）dlopen 正常，
   `libwayland-cursor.so.0.22.0`（签名失效）→ EACCES —— 结果差异只来自签名状态。

### 与既有条目的边界（去重说明）
| 条目 | 该条根因/错误面 | 本条差异 |
|------|----------------|---------|
| DRAFT-12412（zsa-wally lld 占位 codesign） | 新链接产物带 lld 占位 `.codesign` + 配方 has-signature 早退守卫（子串匹配）误判已签 → exec EPERM | 本条是**下载来的**预编译包签名本身失效（无配方逻辑 bug）；新增 **dlopen EACCES(13)** 错误面（该条仅 exec EPERM） |
| DRAFT-13388（musl ldso conan 包 symlink） | /data 卷上 musl ld.so 无法经 symlink 加载（仅本地场景，CI 不受影响） | 本条是包树路径**签名校验**，CI 与本地均触发，与 symlink 无关 |
| E083（BiSheng JDK 签名匹配） | JDK NativeLibraries.load() 额外做 JVM 签名**匹配**校验（该场景 C 层 dlopen 不校验签名） | 本条实测包树路径 dlopen 无效签名在**内核/加载器级**被拒（EACCES）——校验层/场景不同，两条不矛盾，排查时先按本条路径对照实验区分 |

## 推荐方案（已验证）
**方法**: strip-invalid-codesign-and-selfsign（移除失效签名段 + 自签）

**宿主构建工具**（build()/generate() 内调用，如 wayland-scanner、glib-compile-resources）：
```
1. 复制工具到 build 私有目录（不改包树原文件）
2. llvm-objcopy --remove-section .codesign <tool>
3. binary-sign-tool sign -selfSign 1 -inFile <tool> -outFile <tool>.s -signAlg SHA256withECDSA
4. mv 回 + chmod 755（HMDFS 上 chmod 被忽略，执行不依赖权限位）
5. tc.binaries 注册 / LD_LIBRARY_PATH wrapper 调用（conanbuild 环境）
```

**运行时 .so 依赖**（如 rofi 主二进制 dlopen libwayland-cursor）：
```
1. package() 内：从依赖包复制目标 .so → 移除签名段 → 重签 → 放入本包 lib/
2. cpp_info.libdirs = ["lib"] —— VirtualRunEnv 将本包 lib 置于消费者 conanrun LD_LIBRARY_PATH
   先于依赖包 lib（直接依赖优先）
3. dlopen 解析到重签副本 → EACCES 消除
```

**验证**: rofi 2.0.0 三处实证（wayland-scanner、glib-compile-resources、libwayland-cursor），
重签副本 dlopen/执行全部通过，消费者 `rofi -v` → exit 0 "Version: 2.0.0"，上游测试 18/18。
**仓内先例**: appstream/1.2.0（工具签名）、aravis（共享库重签 _sign_shared_libs）。

## 回退方案
推动 ohpcd 制品仓侧对该依赖包**重新签名发布**（根治，可另立依赖项任务，如 wayland/1.22.0 的
libwayland-cursor）；绕行期间配方保留重签逻辑，上游修复后移除。

## 禁止策略
- **chmod 权限位修改**：根因是签名校验而非 POSIX 权限（HMDFS 上 chmod 亦被忽略）——无效且误导。

## 验证证据（rofi 2.0.0，2026-10-16）
- 修复前：包树 `libwayland-cursor.so.0.22.0` dlopen → errno=13；同包 client 库 → OK（对照）
- 修复前：包树内 wayland-scanner/glib-compile-resources 执行 → rc=126（Operation not permitted）
- 修复后：conan create / conan-verify（G0-G4+L2/L4/L5）/ W3 本地 CI 模拟全绿（.ci-result.json exit_code=0）
- 消费者用例：`rofi -v` exit 0，输出含 Version: 2.0.0

## 关键词
EPERM, rc=126, EACCES, errno 13, .codesign, .conan2, 包树, binary-sign-tool, selfSign, llvm-objcopy, remove-section, dlopen, ohpcd, 失效签名

## 关联条目
- similar_to: DRAFT-12412-zsa-wally-ohos-lld-placeholder-codesign / DRAFT-13388-musl-ldso-cannot-load-through-conan-package-symlinks / E083

---
*草稿提交无需审核即可通过；主编审核 promote 为正式 E 条目时保留本作者信息。*
