# OHOS 真机拒绝执行"非预置 ELF"（chmod 后仍 Permission denied）；工具/代码生成器类依赖改为本机预生成构建图/产物

- **草稿 ID**: DRAFT-libskia-146.20260602-git.3476902-nonprestaged-elf-exec-denied
- **来源**: libskia 146.20260602-git.3476902 HarmonyOS PC 适配（真机 gn 不可执行 → 本机预生成 out/ 构建图，Plan C）
- **分类**: conan / ohos / hmdfs / exec-policy / build-tool / gn / ninja / cross-compile / toolchain
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **在真机上执行新上传/拷贝的 ELF 工具（如 gn）时**：
  ```
  /storage/Users/currentUser/tmp/gn: Permission denied
  /storage/Users/currentUser/.local/bin/gn: Permission denied
  ```
  - `ls -l` 显示 `-rwxr-xr-x`（权限位正确、属主正常、文件可读）；
  - `chmod 755` / `chmod 777` / `os.chmod(..., 0o777)` 后**仍然** `Permission denied`；
  - 换落点（`$HOME/tmp`、`$HOME/.local/bin`、conan cache 目录、`usr/local/bin` 副本）全部无效；
  - 而**同目录预置的 clang-15 / ninja / python3 / ar / ld.lld（owner=file_manager）可正常执行**。
- **复现命令**：`conan create` 在 OHOS aarch64 真机上执行配方里调用的 `bin/gn gen` 或任何用户侧 ELF。

## 根因

1. HarmonyOS 真机 `/storage` 为 **HMDFS**（HarmonyOS Distributed File System），
   叠加 **SELinux/域标签执行策略**：只有"预置/受信"二进制（部署于预置可执行目录、
   owner=file_manager 等受信域）被允许 `execve`。
2. 用户在会话中上传/拷贝/新建的 ELF 属于"非预置域"，即使 st_mode 含执行位、属主正确，
   内核/策略层在 `execve` 时仍返回 `Permission denied`——**与文件权限无关，是执行策略拦截**。
3. 因此"把工具二进制打包进源码、真机解压后运行"的通用做法在 OHOS 真机**不成立**。

## 最小修复方案（推荐）

**在宿主（开发机）预生成构建产物，真机只跑预置工具链。**

以 GN+ninja 项目（Skia 等）为例：

1. 宿主侧用本机 gn 生成构建图，工具链路径**直接写成真机绝对路径**：
   ```python
   # 本机（Windows/Linux）：gn gen out --args 含
   #   cc  = "/storage/Users/currentUser/usr/local/bin/clang"
   #   cxx = "/storage/Users/currentUser/usr/local/bin/clang++"
   #   target_os="linux" target_cpu="arm64"（OHOS clang 交叉）
   ```
2. **打包前对构建图做"真机化 rewrite"**（gn 在 Windows 生成的图混入宿主路径与命令）：
   - `cmd.exe /c echo > ${out}` → `: > ${out}`（真机无 cmd.exe；stamp 用 sh 内建）；
   - `D$:/harmonyos/...` 等转义绝对路径 → `../`（相对 out/，真机解包后指向源码树）；
   - 命令里 `<...>` 宏值（如 freetype 的 `-DFT_CONFIG_MODULES_H=<freetype-android/...>`）
     加引号，否则 ninja 对含 `<` 的命令走 `/bin/sh -c`，sh 把 `<>` 当重定向报
     `can't open <freetype-android/...>`；
   - 递归扫描 `out/**/*.ninja` 确认 `D$:`、`cmd.exe`、宿主盘符零残留。
3. 真机配方 `build()` 检测 `out/build.ninja` 存在 → **跳过 gn gen**，直接
   `ninja -C out -j2 skia`（ninja 走真机预置 PATH）；`-j` 按 `/proc/meminfo` MemTotal 限流
   （`max(2, min(4, mem_mb//8000))`），防 OOM 关真机。
4. 其他构建系统同理：bison/flex/yacc、protoc、gperf、cmake 代码生成器——本机生成 `.c/.h/.pb.cc`
   随源码包上传，真机只做编译链接。

**对照结论**：不要试图在真机上传执行新 ELF；任何"真机下载工具 / chmod 工具 / 拷贝工具到
$HOME 各目录"的组合都无法通过 HMDFS 执行策略。

## 实际验证结果

- **真机**：HarmonyOS HongMeng Kernel 1.12.0 aarch64（clang 15.0.4），profile `ohos-aarch64`。
- **构建**：`conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` 通过
  —— `[1213/1213] link libskia.a`，package 生成 377 头文件 + libskia.a（21,080,060 B，ar archive）。
- **消费者用例（2 个，均实跑通过）**：
  1. `test_skia.cpp`：SkSurface 画红矩形 → 像素断言 RGBA(255,0,0,255)（SkSurfaces/SkCanvas/SkPaint）；
  2. `test_skia2.cpp`：SkBitmap → SkImage → PNG 编码 → PNG 8 字节魔数校验
     （验证 bundled libpng 集成）。
- **对照（死路验证）**：真机 `os.chmod(gn, 0o777)`、`cp` 到 `$HOME/tmp` / `$HOME/.local/bin` /
  conan cache 后执行，均 `Permission denied`；同目录预置 clang-15 ELF 可执行。

## 适用范围

- 在 HarmonyOS PC（HMDFS）真机上构建/适配任何需要在构建机运行**额外二进制工具**的三方库
  （GN/ninja 项目的 gn；代码生成器 bison/flex/protoc/gperf；构建期下载的工具 ELF）。
- 任何 `exec` 报 `Permission denied` 且 st_mode 正确、chmod 无效的场景。

## 非适用边界

- 无需额外工具的纯编译/链接库不受影响（预置 clang/ninja 即可完成全流程）。
- 目标环境为常规 Linux（ext4/tmpfs、无 HMDFS 执行策略）时无需此处理。
- 若平台侧可将工具加入预置/受信路径（owner=file_manager 域），可申请白名单替代本机预生成。

## 查重差异

- 与 DRAFT-libfreenect-0.5.3-hmdfs-shared-lib-versioned-symlink（HMDFS 不支持 symlink）同属
  HMDFS 家族但**维度不同**：本条是 **exec 执行策略**（非预置 ELF 不可执行），freenect 条是
  **文件系统软链能力**；本条目给出"本机预生成构建产物"这一通用绕过范式。
- 与 E092（CMake 平台识别）不同：本条不涉及平台识别，涉及**构建期工具执行策略**。
- 经查知识库无"OHOS HMDFS 拒绝执行用户侧 ELF / 本机预生成构建图"先例条目。

## 关联原则

- P010：尊重上游构建逻辑，用 Conan 配方侧最小改动（跳过 gn gen、直跑预置 ninja），不改上游源码。
- P020：消费者测试必须真实调用 API（SkSurface 画图验像素 / PNG 编码验魔数），非空壳。

## 禁止模式

1. **反复 chmod（755/777）后重试**：HMDFS 执行策略与 st_mode 无关，必然仍 `Permission denied`。
2. **真机下载/放置新 ELF**（curl/wget 到 $HOME、cp 到 .local/bin、cache）：同样落入非预置域。
3. **用 `#ifdef __OHOS__` 宏改上游源码**：不符合配方侧最小替换约定，污染上游源码树。
4. **消费者测试空壳打印**：必须真实调用被测 API 并做断言。

## 关联交付

- 本草稿与 `archives/l/libskia/146.20260602-git.3476902/**` 同属一次交付。
- 正式 E 编号由知识库主编审核后分配。
