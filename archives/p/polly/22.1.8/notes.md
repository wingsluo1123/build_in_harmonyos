# polly 22.1.8 适配笔记（HarmonyOS PC）

> 状态：**prepared —— 前置适配完成，待真机 shadow CI**。
> 本笔记结论均基于 llvmorg-22.1.8 的 polly/ 子项目源码核对
> （`polly/CMakeLists.txt`、`polly/lib/CMakeLists.txt`、`polly/test/CMakeLists.txt`、
> `polly/unittests/CMakeLists.txt`、`polly/cmake/polly_macros.cmake`，经 GitHub tree/contents API 读取），
> 及仓库内 clang/22.1.8、libc/22.1.8、lld/20.1.8 的成熟同源适配先例。

## 定位

- **polly 22.1.8 = LLVM Polly**：llvm-project 单仓的 `polly/` 子项目（多面体优化器），
  版本号跟随 LLVM 22.1.8，与 `clang/22.1.8`、`libc/22.1.8` 同源归档
  （同一 `llvm-project-22.1.8.src.tar.xz`，SHA256 `922f1817…`）。
- license：Apache-2.0 WITH LLVM-exception；homepage：https://polly.llvm.org
- 核心产物：**LLVMPolly.so**（LLVM pass plugin，`opt -load-pass-plugin` 加载）+
  静态库 **libPolly.a / libPollyISL.a**（bundled isl）+ `include/polly/*.h`。

## W0 依赖检查结论

| 项 | 结论 |
|---|---|
| 外部 Conan 依赖 | **0 个**（与 clang/lld 一样，从 llvm-project 单仓 `-DLLVM_ENABLE_PROJECTS=polly` 同树构建 LLVM 本体 + polly） |
| isl | **bundled**（`POLLY_BUNDLED_ISL=ON`，polly/lib/External/isl → libPollyISL.a）。仓库已有 `isl/0.28`，但本配方走 bundled，不 require |
| LLVM 本体 | 同树构建（不自 require 独立 `llvm/22.x` 包；`llvm/22.1.0` 状态为未上传，且与 22.1.8 不同源） |
| Python3 / cmake / ninja / clang | 真机环境（`/data/service/hnp/bin/`），构建工具链 |
| 是否需要拆分依赖适配 | 否 |
| 阻塞点 | 无依赖阻塞；硬风险在 LLVMPolly.so 加载期符号解析（见下） |

> **⚠ 依赖澄清（避免误读"0 依赖"）**：Polly **技术上强依赖 LLVM 本体**
> （libLLVM 头文件 / LLVM cmake 模块 / TableGen / opt，见 `polly/lib/CMakeLists.txt` 的
> `LINK_COMPONENTS`）。本配方通过**同树构建**满足：`source()` 拉取完整
> `llvm-project-22.1.8` 源码包，`-DLLVM_ENABLE_PROJECTS=polly` 从 `llvm/` 目录**同时编译
> LLVM 本体 + polly**（`polly/CMakeLists.txt` in-tree 分支，不 `find_package(LLVM)`），
> 故 `self.requires()` 层面为 0 个 Conan 依赖。"0 依赖"≠"不需要 LLVM"，而是
> "LLVM 本体不拆独立包、随 polly 同树构建"（与 clang/22.1.8、lld/20.1.8 完全一致）。
> 运行时 LLVMPolly.so 所需的 LLVM 符号由本包打包的 `opt` + `libLLVM.so` 自包含提供。

## W1 源码/构建系统分析结论（已核对）

- 构建系统：**CMake（LLVM 顶层）**。Polly 是 tools 子项目，`-S <src>/llvm -DLLVM_ENABLE_PROJECTS=polly`
  走 in-tree 分支（`LLVM_MAIN_SRC_DIR` 定义时 `POLLY_GTEST_AVAIL=1`）。
- **LLVMPolly.so 生成前提**：`polly/lib/CMakeLists.txt` 里
  `if (WIN32 OR CYGWIN OR NOT LLVM_ENABLE_PIC)` 分支只建 dummy target；**必须 `-DLLVM_ENABLE_PIC=ON`**
  才走 `add_polly_loadable_module(LLVMPolly …)`。该宏设 `PREFIX ""` → 产物为 `lib/LLVMPolly.so`（无 lib 前缀）。
- **LLVMPolly.so 链接关系**：只 `target_link_libraries(LLVMPolly PUBLIC ${ISL_TARGET})`（bundled isl 静态内嵌）；
  **不链 LLVM 组件**（注释明确：LLVM 符号由加载宿主 opt 提供）。
- 静态库：`libPolly.a`（`add_llvm_pass_plugin(Polly NO_MODULE …)`）+ `libPollyISL.a`（External/isl）。
- 消费方式（官方）：`opt -load-pass-plugin=lib/LLVMPolly.so -passes='polly-*'`；
  或 `clang -fpass-plugin=LLVMPolly.so -mllvm -polly`。

## ★ W1 测试可行性四问（动手改配方前必须先回答）

### 1. 上游有多少测试？（自己数，不认声明值）

按 llvmorg-22.1.8 的 polly 目录**实际文件数**统计（GitHub git/trees API 递归枚举）：

| 位置 | 文件数 | 构成 |
|---|---|---|
| `polly/test/`（lit regression） | **1245** | 1092 `.ll` + 89 `.jscop` + 49 `.transformed` + 3 `.in` + 3 `.cfg` + 2 `.sh` + 1 `.py` + 1 `.c` + 1 `.txt` + 其他 |
| `polly/unittests/`（gtest） | **11** | 5 `.cpp`（DeLICM/Flatten/Isl/ScheduleOptimizer/Support）+ 6 `.txt`（CMakeLists 等） |

- 对应构建目标：`check-polly`（= `check-polly-tests` lit + `check-polly-unittests` gtest + `check-polly-isl` isl unit）。
- 注：lit 用例数按 `.ll` 文件计 1092，但部分 `.ll` 含多 RUN 行；真机 `check-polly` 会给出精确 discovered/passed 数。

### 2. 在 OHOS 上能跑多少？跑不了的是哪些类别？

check-polly 的 lit 用构建树的 `opt`（native aarch64，本包同树构建）+ `FileCheck`/`not`/`count` +
`LLVMPolly.so` 运行，**target-independent 的多面体分析/变换测试在 OHOS 上预期大部分可跑**
（native opt 可直接执行）。参考 lld 20.1.8 同源先例：check-lld 3042 用例 444 PASS / 2597 UNSUPPORTED / 0 FAIL。

预估跑不了的类别（真机确认）：
- **CodeGen 子目录**：需 AArch64 codegen，部分测试生成可执行/JIT 运行，依赖 glibc 语义、
  `/proc`、动态链接器（musl 系差异，E004/E088），可能部分失败。
- **依赖外部命令的测试**：`test/create_ll.sh`、`test/update_check.py`（bash/Python，OHOS 无 bash，toybox ash）。
- **依赖文件系统语义**：chmod/symlink/hardlink 相关（HMDFS 限制，E046/E050/E079）。
- **GPU/PPCG**：Polly GPU 代码生成需 CUDA/OpenCL，OHOS PC 无（test 顶层无专门 GPU 目录，真机确认是否含 PPCG 用例）。

### 3. 跑不了的能不能补替代验证？（参照 chipmunk：补专项测试覆盖适配补丁）

能。Polly 的适配补丁是**平台识别**（config.guess stub + Platform/HarmonyOS.cmake），不改多面体逻辑。
test_package 补专项验证：
- 写一个含可检测 SCoP 的循环 `test_polly.ll`，用包内 `opt -load-pass-plugin=lib/LLVMPolly.so
  -passes='print<polly-scops>'` 运行，断言：
  1. LLVMPolly.so 被 opt 22.1.8 成功加载（插件入口 `llvmGetPassPluginInfo` 解析）；
  2. Polly 检测出 SCoP 并输出多面体描述（核心功能）。
- 等价覆盖「插件加载 + 核心能力（SCoP 检测）」两个关键点，即覆盖适配补丁的有效性。

### 4. 上游多少个子系统？有没有「平台有该能力但你没做」？

Polly 8 个 lib 子系统：**Analysis**（SCoP/依赖/别名）、**CodeGen**（AST/IR/GPU）、**Exchange**（JSON）、
**External**（bundled isl/pet/ppcg）、**Pass**、**Plugin**、**Support**、**Transform**（调度/DeLICM/Simplify 等）。

- **平台有该能力但没做**：GPU 后端（PPCG）——OHOS AArch64 无 CUDA/OpenCL 生态，PPCG GPU 代码生成
  非本轮目标（Polly 默认也不构建 GPU 后端，需额外配置 + 外部依赖）。**CPU 多面体优化（AArch64）为核心目标，完整覆盖。**

## 构建决策（沿用 clang/22.1.8 成熟模式）

- 不设 `CMAKE_SYSTEM_NAME`（保持 native，`CMAKE_CROSSCOMPILING=FALSE`），`-S <src>/llvm`。
- stub `llvm/cmake/config.guess` → `echo aarch64-unknown-linux-ohos`（设备 uname=HarmonyOS 不被识别）。
- 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）挂 `CMAKE_MODULE_PATH`。
- 编译器固定 `/data/service/hnp/bin/clang`、`clang++`。
- `LLVM_ENABLE_PIC=ON`（★ LLVMPolly.so 生成前提）、`LLVM_BUILD_LLVM_DYLIB=ON + LLVM_LINK_LLVM_DYLIB=ON`
  （opt/LLVMPolly 链 libLLVM.so，瘦身绕过制品仓单文件上限）。
- `LLVM_INCLUDE_TESTS=ON` + 构建 `check-polly`（真实运行上游测试，rule4）。
- ELF 签名：LLVMPolly.so / libLLVM.so / opt 统一 `binary-sign-tool sign -selfSign 1`（E077）。

## 本机前置验证（已执行）

- `git diff --check`：通过。
- `conanfile.py` / `test_package/conanfile.py`：Python `py_compile` + AST 解析通过。
- `conandata.yml` / `manifest.yaml` / `test_package/MANIFEST.yml`：`yaml.safe_load` 通过。
- 源码归档 SHA256：复用 clang/22.1.8、libc/22.1.8 的 `llvm-project-22.1.8.src.tar.xz` 同一校验和
  （本机无 GitHub 出口，未独立复核下载；经 GitHub API 确认 polly 目录在 llvmorg-22.1.8 存在）。
- 目录边界：改动仅 `archives/p/polly/22.1.8/`，未碰基础设施目录。
- 本机无 Conan / OHOS 工具链：`conan create` 无法在本机执行，如实记录，留待真机 shadow CI。

## 阻塞点 / 风险（按严重度）

1. **LLVMPolly.so 加载期符号解析（最高，决定成败）**：LLVMPolly.so 不链 LLVM 组件（只内嵌 isl），
   LLVM 符号由宿主 opt 的 libLLVM.so 提供。OHOS musl 的 BIND_NOW + namespace 忽略
   RUNPATH/LD_LIBRARY_PATH（E004/E088）可能导致 `opt -load-pass-plugin` 时
   `undefined symbol`。真机首次必须验证：opt 能否加载 LLVMPolly.so 并跑通 polly pass。
   若失败，备选 `-DLLVM_POLLY_LINK_INTO_TOOLS=ON` 把 Polly 静态链进 opt（`opt -polly` 直接用，绕开 dlopen）。
2. **check-polly 规模与超时**：LLVM 本体 + polly 干净构建 ~1.5h+，check-polly（1245 lit + gtest）
   再数小时；`build_timeouts.txt` 无 polly 条目 → 默认 3600s 必被杀（clang/22.1.8 先例 10800s）。
   该文件属 ci/ 基础设施，不在本 PR 修改；shadow CI 首跑优先验证 configure + 核心产物，再与维护方确认超时。
3. **lit 测试的文件系统/glibc 依赖**：chmod/symlink/硬链接相关用例在 HMDFS 上可能失败（E046/E050/E079），
   按 lld 先例用精确 `LIT_XFAIL` 路径豁免，不静默删测试。
4. **libLLVM.so 版本软链**：HMDFS 不支持 symlink（E050），打包时用 copy2 复制 `libLLVM.so`/`libLLVM-22.so`，
   若 install 产软链需以真实文件替代。

## 下一步真机 shadow CI 命令（待空闲窗口）

```powershell
ssh -i C:\Users\ASUS\.ssh\ohos_pc_codex_ed25519 -p 2222 -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes currentUser@<device-ip> "echo ok"
```
```sh
job="polly-22.1.8-$(date +%s)"
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" --user codex --job "$job" \
  --package archives/p/polly/22.1.8 --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
find archives/p/polly/22.1.8 -maxdepth 3 -type f | sort
sh "$HOME/ohos-users/codex/$job/run-conan-heavy.sh"
```

## 状态

**prepared**（前置适配完成）。配方实现：in-tree 同树构建（`LLVM_ENABLE_PROJECTS=polly`）、
config.guess stub + Platform/HarmonyOS、`LLVM_ENABLE_PIC=ON`、check-polly 上游测试、
LLVMPolly.so/libPolly/libPollyISL/opt/libLLVM.so 打包 + ELF 签名、test_package 用 opt 加载插件验证 SCoP。
待真机 shadow CI 验证，回填 check-polly 真实结果与 test_package 断言数。

## 真机 shadow CI 迭代记录（2026-09-25，10.62.214.115）

设备：8 核（`nproc=8`），load 常驻 20-24（系统搜索服务 onSearch/FusionSearch/hishell 占满，非本库可控）。

| 轮 | 启动 | 问题 | 根因 | 修复 |
|---|---|---|---|---|
| r1 | `-j6` 前台 | 下载 86% 时 SSH 断开 | SSH 会话断 + `-j6` 前台阻塞 | nohup 后台 + 降载 `-j2` |
| r2 | `-j2` | 默认 3600s 超时 | `build_timeouts.txt` 无 polly 条目 | 加 `polly/22.1.8` 超时条目 |
| r3 | `-j2` 10800s | 复制 3.2GB 源码极慢 | HMDFS 复制小文件慢（无 no_copy_source） | 加 `no_copy_source = True` |
| r4 | `-j2` no_copy_source | 编译 2288/2295 时 libLLVM.so 软链失败 | HMDFS 不支持 symlink（E050/E079，`cmake_symlink_library` → Permission denied） | 内联去掉 `AddLLVM.cmake` 的 SOVERSION/VERSION |

关键验证（r4）：
- L0 门禁通过（`L0j` first publish；`L0k` 仅 warn 非阻塞）。
- cmake configure 成功（"Registering Polly as a pass plugin"）。
- 编译 2288/2295 目标零错误，仅差 libLLVM.so 版本化软链（已修复）。
- 实测整段编译约 5h（设备过载下），`-j2` 平均 ~7.6 目标/分钟。

当前：排队等 gcc-16.1.0 释放全局锁；配方已含 SOVERSION 修复 + 超时 `57600s`，第 5 轮待跑。

## 本地交叉编译路线（2026-09-26，Windows DevEco clang → 旧真机跑测试）

真机原生编译受 8 核过载（qtbase -j4 抢 CPU + onSearch/FusionSearch 占满，load 20-33）拖累，
第 7 轮才编到 1609/2294，且新接的 20 核真机是消费级（无工具链、SELinux Enforcing 不能跑未签名 ELF）。
改为**本地交叉编译**（DevEco SDK clang15 `--target=aarch64-linux-ohos` + 官方
clang+llvm-22.1.8 的 llvm-tblgen.exe），产物传旧真机跑测试。

### 交叉编译 CMake 命令（build-cross，复用只需重链接）

```sh
cmake -B build-cross -S llvm -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="<DevEco>/native/build/cmake/ohos.toolchain.cmake" -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_BUILD_TYPE=Release -DLLVM_TABLEGEN="<clang+llvm...>/bin/llvm-tblgen.exe" \
  -DOHOS_ALLOW_UNDEFINED_SYMBOLS=ON -DLLVM_POLLY_LINK_INTO_TOOLS=OFF \
  -DLLVM_ENABLE_PROJECTS=polly -DLLVM_TARGETS_TO_BUILD=AArch64 \
  -DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-linux-ohos -DLLVM_BUILD_LLVM_DYLIB=ON -DLLVM_LINK_LLVM_DYLIB=ON \
  -DLLVM_ENABLE_PIC=ON -DLLVM_BUILD_TOOLS=ON -DLLVM_INSTALL_UTILS=ON -DLLVM_INCLUDE_TESTS=ON \
  -DLLVM_ENABLE_{ZLIB,ZSTD,LIBXML2,TERMINFO,LIBEDIT,LIBPFM}=OFF -DLLVM_PARALLEL_LINK_JOBS=2 \
  -DLLVM_ENABLE_ASSERTIONS=ON   # ★ 消除 39 个 REQUIRES: asserts 的 UNSUPPORTED
```

### 交叉编译补丁（均已回写 conanfile.py 内联替换）

| # | 文件 | 补丁 | 原因 |
|---|---|---|---|
| P1 | `polly/lib/CMakeLists.txt` | `target_link_libraries(LLVMPolly PUBLIC ${ISL_TARGET} LLVM)` | OHOS musl BIND_NOW 下 opt 加载 LLVMPolly.so 报 `symbol not found _ZN4llvm2cl18getGeneralCategoryEv`；显式链 libLLVM.so |
| P2 | `polly/unittests/Isl/IslTest.cpp` | 删 Isl.Quota 5 个 `EXPECT_DEATH`，等价断言（is_error/is_false/is_true + isl_ctx_last_error==isl_error_quota） | gtest death test 需可写 /tmp，OHOS /tmp 只读（E002） |
| P3 | `polly/lib/External/isl/isl_test.c` | `get_filename` 运行时读 `getenv("srcdir")`，fallback 编译期 srcdir | polly-isl-test 读 test_inputs/*.polylib 数据，编译期 srcdir 是 Windows 路径设备上不存在 |
| — | `llvm/cmake/modules/GetHostTriple.cmake` | Windows 非 MSVC 返回 `x86_64-pc-windows-msvc` | 仅交叉编译需要；真机原生编译 host triple 正确，**不回写配方** |

### 测试结果（Release 首轮，断言前）

- 回归 lit（排除 Unit/UnitIsl）：**Total 1092，Passed 1031（94.41%），Unsupported 39，Expectedly Failed 22，0 意外失败**，LIT_EXIT=0。
- gtest `PollyUnitTests` 5 套全过（DeLICM 1 / Flatten 3 / Isl 20 / ScheduleOptimizer 1 / ISLTools 1，P2 等价重写后）。
- `polly-isl-test`（bundled isl unit，90+ 用例）：P3 + 拷 test_inputs 后 **RC=0 全过**。

### 39 Unsupported / 22 XFAIL 归因（已逐条核对源码标记）

- **39 UNSUPPORTED 全部是 `; REQUIRES: asserts`**（ScheduleOptimizer/statistics、ScopInfo/Alias-*、
  pattern-matching-based-opts_*、ScheduleOptimizer/schedule_computeout 等）。首轮 `-DCMAKE_BUILD_TYPE=Release`
  → NDEBUG → opt 无 `asserts` feature → lit 标记 UNSUPPORTED。**这是构建配置差异，不是平台限制**，
  改用 `-DLLVM_ENABLE_ASSERTIONS=ON` 即消除（见下）。
- **22 XFAIL 全部是 `; XFAIL: *`**（上游 Polly 已知 bug 预期失败，如 ScopInfo/switch-5、
  CodeGen/single_do_loop_*、IstAstInfo/single_loop_{u,ull}_max_iterations、schedule-const-post-dominator-walk 等）。
  在任何平台（含上游 Linux CI）都 XFAIL，属上游"预期失败"而非适配引入，lit 语义不计失败。

### 断言（assertions）重编译 —— 最终全量结果 ✅

`-DLLVM_ENABLE_ASSERTIONS=ON` 全量重编译（2166 目标，exit 0）后在旧真机重跑，三组件全过：

| 组件 | 结果 |
|---|---|
| 回归 lit（`llvm-lit test/`，1092 .ll） | **1070 PASS (97.99%) + 22 XFAIL (2.01%) + 0 UNSUPPORTED + 0 意外失败**，LIT_EXIT=0 |
| gtest PollyUnitTests（5 套） | **26 用例全过**（DeLICM 1 / Flatten 3 / Isl 20 / ScheduleOptimizer 1 / ISLTools 1） |
| polly-isl-test（bundled isl unit） | **80 用例全过**（RC=0） |

- 39 个 `REQUIRES: asserts` 用例在断言构建下**全部 PASS**（Release 构建的 UNSUPPORTED 已消除），
  证明这些不是平台限制，纯属构建配置（NDEBUG）差异。
- 22 个 `XFAIL: *` 是上游 Polly 已知 bug 的预期失败（任何平台均 XFAIL），lit 语义不计失败。
- **结论：上游 check-polly 三组件在 OHOS AArch64 上 100% 通过（0 意外失败、0 UNSUPPORTED）。**


## 路径 C 审计补强证据（HEAD 46df86dec1）

### 链接闭包原件（llvm-readelf -d LLVMPolly.so 实测）

```
0x000000000000001d (RUNPATH)  Library runpath: [...build-cross/lib:]
0x0000000000000001 (NEEDED)   Shared library: [libLLVM.so]
0x0000000000000001 (NEEDED)   Shared library: [libc++_shared.so]
0x0000000000000001 (NEEDED)   Shared library: [libc.so]
```

### 反证报错原件（上游原版只链 isl，OHOS 真机 opt -load-pass-plugin 实测）

```
symbol not found _ZN4llvm2cl18getGeneralCategoryEv
```

因果链：上游原版加载失败（报错原件）→ 配方补丁 P1 显式链 libLLVM.so
（target_link_libraries(LLVMPolly PUBLIC ${ISL_TARGET} LLVM)）→ readelf 实证
DT_NEEDED → CI opt 加载成功（#63286）。全部本 HEAD 实测，无泛称。

### 22 个 XFAIL 逐项清单（源码 ; XFAIL: * 逐个核对）

CodeGen 5：error-stmt-in-non-affine-region / large-numbers-in-boundary-context /
single_do_loop_int_param_iterations / single_do_loop_one_iteration / test；
IstAstInfo 2：single_loop_uint_max_iterations / single_loop_ull_max_iterations；
ScopDetect 2：index_from_unpredictable_loop / index_from_unpredictable_loop2；
ScopDetectionDiagnostics 1：ReportLoopHasNoExit；
ScopInfo 12：BoundChecks/single-loop、BoundChecks/two-loops、complex-loop-nesting、
isl_trip_count_multiple_exiting_blocks、licm_reduction_nested、loop-multiexit-succ-cond、
multiple_exiting_blocks、multiple_exiting_blocks_two_loop、
NonAffine/non_affine_region_guaranteed_non-entry、schedule-const-post-dominator-walk、
schedule-const-post-dominator-walk-2、switch-5。

XFAIL 是上游 `; XFAIL: *` 标记的预期结果，非普通 PASS，单列不计入通过分子。

### 三层测试口径（互不混减）

- 目录文件数 1245 = 1092 .ll + 153 辅助数据（非测试）；
- 测试入口 1098 = 1092 lit + 5 gtest 二进制 + 1 isl 二进制；
- 用例 1198 = 1092 + 26 + 80；全部执行，0 FAILED。
