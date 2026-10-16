# libskia 146.20260602-git.3476902 适配笔记

## 编译环境
- 构建系统: GN (meta-build) + ninja；**构建图（out/）本机预生成，真机直跑 ninja**
- 本机前置完成日期: 2026-10-04 → 2026-10-13（P1 完整源码包路线）
- **真机 W3 完成日期: 2026-10-14（conan create + test_package 全部通过）**
- 编译器: clang/clang++（OHOS aarch64 交叉，profile `$HOME/.conan2/profiles/ohos-aarch64`）
- 状态: **W3 PASSED —— `conan create` 1213/1213 编译 + 打包成功；test_package 冒烟 `libskia smoke ok`**

## 上游识别
- 仓库: https://skia.googlesource.com/skia （GitHub 镜像 https://github.com/google/skia）
- 目标提交: `34769028da93df54a2e33ebe8985413924053bc1`，分支 `chrome/m146`，2026-06-02
- 版本号映射: `146.20260602-git.3476902` = m146 milestone + 日期 + 短 hash
- 官方源码 URL: `https://github.com/google/skia/archive/<full-sha>.tar.gz`（60.6 MB，sha256
  `09605d1152521a358bae574278f311fa93453494b3962ab4d642a94ef3fc17d5`）
- 官方 tarball 不含 third_party → 需 DEPS 同步（见 P1 方案）

## W0 依赖检查
- **Conan 层 requires: 空。** Skia 通过 DEPS 把 freetype2 / libpng / libjpeg-turbo /
  libwebp / zlib / expat / wuffs / dng_sdk / piex 等全部作为 `third_party/externals/` 内置，
  配方 `skia_use_system_*=false`。**没有需要先发布的下游 Conan 依赖。**
- host 侧工具链：`python3` / `ninja` 真机已有（usr/local/bin）；`gn` 真机/CI 无，
  **构建图改为本机预生成**（见 Plan C），真机不再需要可执行 gn。

## P1 完整源码包（核心交付，2026-10-13）

**动机**：真机/CI 与 googlesource 系网络不可达（见下），`tools/git-sync-deps` 与 `bin/fetch-gn`
无法执行。P1 = 在可访问 googlesource 的网络（本机经 127.0.0.1:7897 代理）预先同步并打包。

- **包文件**：`skia-146.20260602-git.3476902-complete.tar.gz`（~84 MB）
- **sha256（最终）**：`a01ea3a20a56bffb226338f89b20e5ff4bdbee6013bd46d4215b4a81600c391e`
  （历史：1d8253fc… v1 含 .git 废包；60dbc7a3… v3 arm64-gn；a12d7ef6…/7a9e83a6… 中间版）
- **内容**（= skia 源码树，无外层目录，conandata 不 strip_root）：
  1. 官方 skia @ 34769028da93df54a2e33ebe8985413924053bc1（完整源码）
  2. `third_party/externals/` **9 个目录**，均精确对齐 DEPS 目标 revision：
     `dng_sdk, expat, freetype, libjpeg-turbo, libpng, libwebp, piex, wuffs, zlib`
     （依据本机 `gn gen` 构建图逐仓核对：仅这 9 个被构建图引用，其余 36 个 DEPS 仓库裁剪；
      已删除全部 `.git` 目录，包内无 git 元数据）
  3. `bin/gn`：linux-arm64 ELF（8.1 MB）——保留作 gn gen 兜底；真机主路径不用它
  4. **`out/`：本机预生成的 ninja 构建图**（Plan C，见下）——真机跳过 gn gen 直跑 ninja

## Plan C（关键决策，2026-10-14）：本机预生成构建图 + 真机只跑 ninja

**问题链**：真机 `conan create` 首次真实构建暴露 4 层问题，最后一层无解：
1. `self.conf.get("tools.build:compiler_executables:c")` 键写法错（Conan 2 应先取整 dict）→ 已修
2. vendor 的 gn 是 linux-amd64，真机 aarch64 → `not executable: 64-bit ELF` → 换 arm64 版重打包
3. shell `chmod` 在 conan build env PATH 找不到 → 改 `os.chmod`
4. **即使 os.chmod 755/777、cp 副本放 $HOME/tmp、$HOME/.local/bin、cache 目录，gn ELF 一律
   `Permission denied`**。对照实验：同目录 usr/local/bin 预置的 clang-15（109MB ELF，owner
   file_manager）可执行，而用户拷贝/新放的 ELF（owner 无论 file_manager 还是自己）都拒执行 →
   **OHOS hmdfs/SELinux 只放行"预置/受信"ELF，用户侧新 ELF 无法 exec**（脚本 shebang 无碍）。

**Plan C 解法**：**不在真机执行 gn**。
- 本机（Windows）用 win gn 以**真机 cc/cxx 绝对路径**为 args 生成 `out/` 构建图
  （is_official_build + target_os=linux + target_cpu=arm64 + minimal 参数）
- **图生成后必须做"真机化 rewrite"**（否则真机 ninja 无法跑）：
  1. `cmd.exe /c echo > ${out}` → `: > ${out}`（stamp；cmd.exe 真机不存在）
  2. `D$:/harmonyos/.tmp/skia-full/` → `../`（gn 在 Windows 会把 include/isystem 写成
     转义绝对路径 `D$:`；ninja 展开后真机指向不存在的 D: 盘）——**两遍替换**：
     普通 `D:/...` 与 ninja 转义 `D$:/...`
  3. `python3 "D:/.../gn/cp.py"` → `python3 "../gn/cp.py"`（脚本相对 out/ 定位）
  4. **freetype 宏值加引号**：`-DFT_CONFIG_MODULES_H=<freetype-android/...>` 无引号时，
     ninja 因命令含 `<` 走 `/bin/sh -c`，sh 把 `<...>` 当重定向 →
     `sh: can't open freetype-android/...`。加引号后 sh 不解析、clang 收到原宏值 ✅
- **真机编译链**：`ninja -C out -j2 skia`（真机 ninja/clang/ar/ld.lld 均为预置，可执行）
- **内存保护**：配方 `_ninja_jobs()` 按 MemTotal 限并发（~1 并发/8GB，clamp 2..4；真机
  23.8GB → -j2，实测编译峰值内存安全）

**args 补充关闭项**（m146 linux target 默认会拉系统依赖）：
`skia_use_fontconfig=false`、`skia_use_x11=false`、`skia_use_harfbuzz=false`
（fontconfig 头真机没有；externals 无 harfbuzz；X11 不需要）——未关则
`fontconfig/fontconfig.h` 编译失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 不含 third_party | Skia 第三方源码走 DEPS/git | P1 完整包预同步（见上） |
| 2 | host 缺 gn | fetch-gn 源不可达 | Plan C 本机预生成构建图；包内保留 arm64 gn 作兜底 |
| 3 | 真机/CI 与 googlesource 系不可达 | 网络策略 | P1 完整包（file:// 本地引用），P2 镜像兜底 |
| 4 | scp 上传失败 `subsystem request failed` | frp 隧道无 sftp subsystem | ssh stdin 管道 `cat > file` 传输 |
| 5 | 首次 prune 未删净（.git 残留 959MB 包） | Windows 只读文件致 rmtree 静默失败 | chmod 解除只读 + onerror 重试；干净包 ~84MB |
| 6 | gn 真机不可执行（Permission denied） | OHOS hmdfs/SELinux 拒非预置 ELF | Plan C：不在真机跑 gn，预生成 out/ 图直跑 ninja |
| 7 | ninja 图含 cmd.exe / D$: 绝对路径 | gn 在 Windows 生成 | rewrite 真机化（`:` stamp、`../` 相对路径） |
| 8 | freetype `sh: can't open ...ftmodule.h` | `<...>` 宏值被 ninja 的 sh 包装当重定向 | 宏值加引号 |
| 9 | `fontconfig/fontconfig.h` not found | linux target 默认开 fontconfig | `skia_use_fontconfig=false`（+x11/harfbuzz） |
| 10 | CMakeDeps 冲突 | test_package 的 generators 属性 + generate() 双实例化 | 删 generators 属性，保留 generate() |
| 11 | conan create 不跑 test_package | test_package/ 目录未上传真机 | 上传后 `conan test` 通过 |

## 真机核查（2026-10-13/14，frp 隧道实测）

**连接**：`ssh -T -p 56267 -i ~/.ssh/id_rsa currentUser@frp-tip.com` ✅（10.62.178.77:2222 超时，弃用）

| 项 | 实测结果 |
|---|---|
| 系统 | HarmonyOS Kernel 1.12.0 aarch64，HOME=/storage/Users/currentUser |
| conan | `$HOME/.local/bin/conan` v2.31.1（OHOS 适配版，支持 os=OHOS） |
| remote | ohpcd（conan.cnb.cool）匿名可连；conancenter disabled |
| profile | `$HOME/.conan2/profiles/ohos-aarch64` 现成（compiler_executables 指向 usr/local/bin/clang） |
| 工具 | python3/clang/clang++/ninja/ar/ld.lld 齐全（usr/local/bin，预置可执行）；git 在 /data/service/hnp/bin |
| TMP | `/tmp` 只读 → 用 `$HOME/tmp` |
| 网络 | github/gh-proxy ✅；googlesource/chrome-infra-packages/storage.googleapis 从真机超时（本机代理 7897 可下） |

## W3 真机构建结果（2026-10-14，最终通过）

```text
[OK] 完整包真机 sha256sum == a01ea3a2...（与本地一致）
[OK] conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
     → [1213/1213] link libskia.a
     → Package '4b977264...' created（377 .h + libskia.a 21,080,060 B, ar archive）
     → Full reference libskia/146.20260602-git.3476902#f3d44b06...:4b977264...#685055b9...
[OK] test_package（conan test）：
     → [100%] Linking CXX executable test_libskia
     → libskia smoke: pixel(2,2)=RGBA(255,0,0,255)
     → libskia smoke ok
```

**耗时参考**：-j2 全量 1213 步约 30+ 分钟（zlib→externals→skia 主体→链接）。

## 阻塞点 / 未决问题
1. **ohpcd 二进制包上传待凭据**：`conan upload libskia/146.20260602-git.3476902 -r=ohpcd --all`
   已确认 ohpcd 需认证（匿名可读不可写）。conan.cnb.cool（GitLab）账号注册中，通过后提供
   用户名 + PAT（scope 含 api/write_registry）→ 真机 `conan remote login ohpcd` 后重传。
2. **PR 承载**：完整包已挂 GitCode Release（见下），PR 只引用 URL+sha，无需随 PR 附 84MB。
3. **shadow CI 复现**：CI 侧需同样的"预生成 out/ 图"注入通道（或 CI 可执行 gn 的方案）。

## 源码包持久化（2026-10-14 已解决）
- **承载**：GitCode Release 附件（tag `libskia-146.20260602-git.3476902`，fork
  gcw_6YxinkyD/build_in_harmonyos）：
  `https://gitcode.com/gcw_6YxinkyD/build_in_harmonyos/releases/download/libskia-146.20260602-git.3476902/skia-146.20260602-git.3476902-complete.tar.gz`
- **验证**：本机全量下载 sha == a01ea3a2… ✅；真机 curl GET 206 ✅；
  真机 `conan source`（新 URL）下载 89.1MB + sha 校验 + 解压 ✅
- **注意**：该 URL HEAD 返回 401（GitCode WAF/ELB 限制 HEAD），GET 正常，conan 不受影响。
- conandata.yml 已切到该 URL（sha256 不变）；真机 file:// 留作本地兜底。

## 下一步（真机 / shadow CI 命令）
```bash
# 真机（已通过，可复跑验证）：
ssh -T -p 56267 -i ~/.ssh/id_rsa currentUser@frp-tip.com
cd /storage/Users/currentUser/tmp-libskia
nohup /storage/Users/currentUser/.local/bin/conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  > $HOME/tmp/libskia-wN.log 2>&1 &   # 内存保护：配方按 MemTotal 限 -j
tail -f $HOME/tmp/libskia-wN.log
# test_package（若 conan create 未自动跑）：
conan test test_package libskia/146.20260602-git.3476902 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64

# 本机重新生成构建图（改动 args 后）：
python D:\harmonyos\.tmp\planc_gen.py        # win gn gen（cc/cxx=真机路径）
python D:\harmonyos\.tmp\rewrite_ninja.py    # cmd.exe→': >'、脚本路径相对化
python D:\harmonyos\.tmp\fix_escaped_paths.py  # D$: 转义路径→../
python D:\harmonyos\.tmp\quote_ft_macros.py    # FT_CONFIG 宏加引号
python D:\harmonyos\.tmp\final_check3.py       # 递归零残留检查
# 然后重打包（tar -czf）+ sha256 + conandata.yml 更新 + 上传 + 真机 conan create

# shadow CI（等 CI 窗口，单包排队错峰）：
CI_PACKAGES="archives/l/libskia/146.20260602-git.3476902" zsh ci/conan/build_and_test.sh
```

## 依赖版本
- 无 Conan 依赖；third_party 版本由上游 DEPS 锁定在该 commit（9 仓，revision 逐仓核对通过）。

## 验证结果
```text
[OK] 源码 URL/sha256 已下载实测（官方 60.6MB + P1 完整包 ~84MB 双 sha256）
[OK] 构建系统识别 (GN+ninja)；gn gen 111 targets 无 error（裁剪前后）
[OK] DEPS externals 逐仓 rev 核对（9 仓精确达标）
[OK] 构建图卫生：递归扫描 out/**/*.ninja：D$: / cmd.exe / D:/harmonyos 全部 0；
     SK_FONTMGR_FCI_AVAILABLE = 0（fontconfig 关）
[OK] conanfile.py / test_package conanfile.py Python AST 语法
[OK] conandata.yml / manifest.yaml / MANIFEST.yml YAML 解析
[OK] 本机 conan source（file://）下载+sha256+解包
[OK] 真机：包上传 sha256 一致；conan source（file://）RC=0
[OK] 持久化：本机全量下载 GitCode 附件 sha == a01ea3a2；真机 GET 206；真机 conan source（gitcode URL）下载+校验+解包
[OK] 真机 W3 conan create：1213/1213 → libskia.a 打包成功（377 h + 21MB .a）
[OK] 真机 test_package：test_libskia 冒烟通过（RGBA(255,0,0,255) → smoke ok）
```

## 注意事项
- 这是图形渲染类深度适配库（R40）：编译通过 ≠ 适配完成。软件光栅路径已跑通；
  后续才考虑 Vulkan/GL GPU 后端与字体。
- 首版只产静态 `libskia.a`（shared 选项保留默认 False）。
- 真机 tmp-libskia 源码树与完整包保留；用毕可清理释放空间（~1GB）。
- **关键经验**：OHOS hmdfs/SELinux 对"用户侧新 ELF"一律拒执行（Permission denied），
  任何工具（gn 等）都应考虑"本机生成/预置部署"，不要试图在真机上传执行新二进制。

## 2026-10-15 路径B收尾：第二消费者用例 + 配方 skcms 打包修复

- 新增 test_package/test_skia2.cpp（SkPngEncoder PNG 编码 + 8 字节魔数校验，验证 bundled libpng 集成）。
- m146 API 勘误：无 include/core/SkEncodedImageFormat.h、无 SkImage::encodeToData；PNG 编码走 include/encode/SkPngEncoder.h 的 SkPngEncoder::Encode(SkPixmap, Options)。
- 头链坑：SkPngEncoder.h -> include/private/SkHdrMetadata.h -> include/core/SkColorSpace.h -> modules/skcms/skcms.h（转发到 src/skcms_public.h，仅依赖 stdbool/stddef/stdint/string）。
- 配方 package() 修复：modules/skcms/ 必须打进 package 根（package_info includedirs=["."]，#include "modules/skcms/skcms.h" 在 -I p/ 下解析）——放 include/modules/ 会仍然失败。
- 真机验证（frp-tip.com:56267，conan test）：2/2 消费者用例通过：
  - test_libskia: pixel(2,2)=RGBA(255,0,0,255) -> smoke ok
  - test_libskia2: png encode 102 bytes, magic ok -> smoke2 ok
- PR_BODY.md 按路径 B 模板成稿（上游通过率 N/A 首轮未运行；新增用例 2/2 100%）；知识草稿
  knowledge/DRAFT-libskia-146.20260602-git.3476902-nonprestaged-elf-exec-denied.{md,kv}。
