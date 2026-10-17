# CMake try-compile 阶段 make 报 resource temporarily unavailable（EAGAIN）——同 head 相邻构建一败一成 = 环境性铁证

- **草稿 ID**: DRAFT-apt-pkg-2.7.14-cmake-trycompile-make-eagain-93480-adjacent-pass
- **来源**: apt-pkg/2.7.14（PR #14901，CI 构建 #93480 失败 / #93481 通过，Worker OpenHarmonyPCDeveloper-CI-012）
- **分类**: cmake / try-compile / make / ci-infra / resource-limits / ohos-platform
- **状态**: 本地草稿（随 PR #14901 提交，待审核 promote）
- **邻近条目**: `DRAFT-apt-pkg-2.7.14-cmake-trycompile-make-eagain-worker`（同包 #90161 同型，但仅有单次失败样本）；本条新增**同 head 相邻构建 #93480→#93481 一败一成**的强判据，环境性定性置信度更高。

## 问题 / 错误签名

- CI `conan-build-test` 阶段 `cmake.configure()` 失败，完整日志（ohpcd.atomgit.com/ci?id=93480）：
  ```text
  Problem parsing /proc/meminfo
  -- The C compiler identification is Clang 15.0.4
  -- The CXX compiler identification is Clang 15.0.4
  System is unknown to cmake, create:
  Platform/HarmonyOS to use this system, ...
  -- Detecting C compiler ABI info - failed
  -- Check for working C compiler: /data/service/hnp/bin/clang - broken
  CMake Error at .../CMakeTestCCompiler.cmake:67 (message):
    The C compiler "/data/service/hnp/bin/clang" is not able to compile a simple test program.
    Run Build Command(s): ... cmake -E env VERBOSE=1 /data/service/hnp/bin/make -f Makefile cmTC_9ed52/fast
    make[1]: Entering directory '.../TryCompile-NlFLfD'
    make[1]: /bin/sh: Resource temporarily unavailable
    make[1]: *** [CMakeFiles/cmTC_9ed52.dir/build.make:81: CMakeFiles/cmTC_9ed52.dir/testCCompiler.c.obj] Error 127
    make: *** [Makefile:134: cmTC_9ed52/fast] Error 2
  -- Configuring incomplete, errors occurred!
  ERROR: apt-pkg/2.7.14: Error in build() method, line 127
      cmake.configure()
  L1_RESULT=fail: conan create failed
  ```
- `L2/L4/L5_RESULT=skip: not run`。
- **决定性旁证**：同一 head `8c44efb0` 的**相邻构建 #93481 由同一 worker CI-012 立即通过**（Conan test_package 通过、L0/L1 门禁通过、conan-build-test ✅）。

## 根因

worker 处于 fd/内存/进程数压力下，CMake 编译器探测试编译（`try_compile` / `cmTC_*` / `TryCompile-*`）用 `make -f Makefile cmTC_*/fast` 派生 clang 编译子进程时，`fork()/posix_spawn()` 返回 EAGAIN（errno 11，日志文本 `resource temporarily unavailable`），make 以 Error 127 退出。CMake 把 try-compile 失败误报为 "The C compiler ... is not able to compile a simple test program" 与 "compiler - broken"，掩盖了资源根因。

排除项（避免误判为配方问题）：
- 本日志 CMake 已正确识别编译器（`The C compiler identification is Clang 15.0.4`），且 `Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++` → **排除 E455**（libstdc++ 误配导致的 try-compile broken）与 #90161 的 "identification is unknown" 场景；
- 错误文本是 `resource temporarily unavailable`（EAGAIN）而非 `/bin/sh: Permission denied` → **排除 E346**（hmmac 拒绝 /bin/sh）；
- 失败点是 make 启动子进程即 EAGAIN，非 clang 编译输出错误；同日志 `Problem parsing /proc/meminfo` 为 worker 内存/资源受限旁证。

## 判定方法

1. **看签名**：同日志出现 `Problem parsing /proc/meminfo`、`make[1]: /bin/sh: Resource temporarily unavailable`、`cmTC_*` try-compile 首次探测即失败（Error 127）；
2. **同 SHA 相邻构建对照（核心判据）**：同一 commit 的相邻两次构建一败一成（#93480 fail → #93481 pass，同一 worker CI-012）→ 唯一变量是执行时刻的 worker 资源占用，环境性定性铁证；
3. **本地同命令复跑**：`CI_PACKAGES="archives/a/apt-pkg/2.7.14" CI_BRANCH="feat/apt-pkg-2.7.14" CI_PR_NUMBER="14901" CONAN_PROFILE=ohos-aarch64-local zsh ci/conan/build_and_test.sh`，本地 `EXIT=0` / `All packages built and tested successfully` 即证明配方无问题。

## 处置（不改配方）

1. 先判环境：对同一 SHA 发起 `/rebuild`，观察是否落到空闲 worker（本 PR 已实证相邻构建 #93481 即通过）；
2. 本地用与 CI 完全相同的 `ci/conan/build_and_test.sh` 复跑，本地全绿即证明配方无问题；
3. 不改包代码、不删测试、不降优化档（直到有设备资源证据——E491 forbid_3）；
4. 若同一 worker 反复稳定复现，可考虑换 Ninja 生成器（直接 exec 编译器，减少 make 层 fork），但优先换 worker。

## 适用范围

- 全部在共享/受限 worker 上走 CMake（`-G "Unix Makefiles"` 默认生成器）的适配，尤其 `cmake.configure()` 在编译器探测试编译（try_compile/`cmTC_*`）阶段失败且报 `resource temporarily unavailable` / `Problem parsing /proc/meminfo`；
- 同型签名还包括 `fork: Out of memory`、`can't fork - try again`、`posix_spawn: Resource temporarily unavailable`、`Bus error`（内存压力下）等间歇性基础设施失败；
- "同一 SHA 相邻构建一败一成"的判定法适用于一切间歇性环境失败排障（先对照再动代码）。

## 边界 / 反例

- 若失败信息是明确的可复现编译错误（`fatal error: ... file not found`、`undefined reference`、`invalid library name in -stdlib`），且同一 SHA 稳定复现，则不是本条目范畴（分别归 E455 / 具体编译错误类条目）；
- 本条目**不**为"跳过测试/伪造通过"提供借口：必须留可复核的日志与本地对照证据。

## 实证

| 项目 | 内容 |
| --- | --- |
| 失败样本 | CI #93480（worker CI-012）：CMake try-compile `make[1]: /bin/sh: Resource temporarily unavailable` → Error 127 → working C compiler broken → `cmake.configure()`（conanfile.py line 127）失败 → L1 fail |
| 通过对照 | 同 head `8c44efb0` 相邻构建 #93481（同一 worker CI-012）立即通过：conan-build-test ✅、test_package ✅、L0/L1 ✅ |
| 前置旁证 | 同日志 `Problem parsing /proc/meminfo`；`-stdlib=libc++` 正确注入（排除 E455）；错误文本 EAGAIN 非 Permission denied（排除 E346） |
| 根因 | worker 资源压力下 CMake try-compile 派生 clang 子进程 fork EAGAIN（环境性，非配方缺陷） |
| 处置 | 同 SHA /rebuild 换空闲 worker（相邻 #93481 已实证通过）+ 本地同命令复跑全绿；不改配方 |

## 关联

- PR：#14901（`feat/apt-pkg-2.7.14`），head `8c44efb0`，构建 #93480（fail）/ #93481（pass）
- 同型条目：`DRAFT-apt-pkg-2.7.14-cmake-trycompile-make-eagain-worker`（#90161，同包同型单样本）；`DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent`（autotools 自举 can't fork）；`DRAFT-ci-worker-gate-fork-oom`（fork OOM）；`DRAFT-vg-1.59.0-fork-eagain-dependency-source-build`（依赖源码构建 fork EAGAIN）
- 正式条目排除：E346（hmmac `/bin/sh Permission denied`，错误文本不同）、E455（libstdc++ 误配，本日志 -stdlib=libc++ 已正确注入）
