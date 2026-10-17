# CMake 编译器探测试编译时 make 报 resource temporarily unavailable（EAGAIN）——worker 资源压力，非配方缺陷

- **草稿 ID**: DRAFT-apt-pkg-2.7.14-cmake-trycompile-make-eagain-worker
- **来源**: apt-pkg/2.7.14（PR #14901，构建 #90161，Worker OpenHarmonyPCDeveloper-CI-022）
- **分类**: cmake / try-compile / make / ci-infra / resource-limits / ohos-platform
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无远端链接，无审核结论）

## 问题 / 错误签名

- CI `conan-build-test` 阶段 `cmake.configure()` 失败，完整日志（ohpcd.atomgit.com/ci?id=90161）：
  ```text
  Problem parsing /proc/meminfo
  -- The C compiler identification is unknown
  -- The CXX compiler identification is unknown
  System is unknown to cmake, create:
  Platform/HarmonyOS to use this system, ...
  -- Detecting C compiler ABI info
  CMake Error: Generator: build tool execution failed, command was:
    .../cmake -E env VERBOSE=1 /data/service/hnp/bin/make -f Makefile cmTC_564f2/fast
  -- Check for working C compiler: /data/service/hnp/bin/clang - broken
  CMake Error at .../CMakeTestCCompiler.cmake:67 (message):
    The C compiler "/data/service/hnp/bin/clang" is not able to compile a simple test program.
    Run Build Command(s): .../make -f Makefile cmTC_7ac1a/fast
    resource temporarily unavailable
  ```
- `L1_RESULT=fail: conan create failed`，`L2/L4/L5_RESULT=skip: not run`。
- 关键旁证：CMake 探测试编译（`cmTC_*` try-compile）是**第一个** fork 密集步骤；同日志中 CMake 自身已报 `Problem parsing /proc/meminfo`。

## 根因

worker 处于 fd/内存/进程数压力下，CMake 探测试编译阶段用 `make -f Makefile cmTC_*/fast` 派生 clang 编译子进程时，`fork()/posix_spawn()` 返回 EAGAIN（`resource temporarily unavailable`，errno 11）。CMake 把 try-compile 失败误报为 "The C compiler ... is not able to compile a simple test program" 与 "compiler - broken"，掩盖了资源根因。

与 libfprint meson EAGAIN 草稿（`DRAFT-libfprint-1.94.10-meson-eagain-unknown-compiler-worker`）、`DRAFT-ci-worker-gate-fork-oom`、`DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent` 同型：**环境性资源失败，非配方/源码缺陷**。

排除项（避免误判为配方问题）：
- 本日志 `Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++` 正确 → **排除 E455**（libstdc++ 误配导致的 try-compile broken）；
- 错误文本是 `resource temporarily unavailable`（EAGAIN）而非 `/bin/sh: Permission denied` → **排除 E346**（hmmac 拒绝 /bin/sh）；
- 失败点是 make 启动子进程即 EAGAIN，非 clang 编译输出错误。

## 判定方法

1. **看旁证**：同日志出现 `Problem parsing /proc/meminfo`、`resource temporarily unavailable`、`cmTC_*` try-compile 首次探测即失败；
2. **查同 SHA 跨 worker 一致性**：同一 commit 在其他构建/本地是否成功（apt-pkg/2.7.14 本地同命令 CI 脚本复现 EXIT=0 全绿；历史多次构建 #78219/#79541/#80045/#85667/#85897/#90161 失败原因各异：curl 缺失 / 429 / EAGAIN，均指向 worker 环境而非配方）；
3. **本地同命令复跑**：`CI_PACKAGES="archives/a/apt-pkg/2.7.14" ... zsh ci/conan/build_and_test.sh`（本机用 `CONAN_PROFILE=ohos-aarch64-local` 适配工具链路径），本地 `EXIT=0` / `All packages built and tested successfully` 即证明配方无问题。

## 处置（不改配方）

1. 先判环境：对同一 SHA 发起 `/rebuild`，观察是否落到空闲 worker；
2. 本地用与 CI 完全相同的 `ci/conan/build_and_test.sh` 复跑，本地全绿即证明配方无问题；
3. 不改包代码、不删测试、不降优化档（直到有设备资源证据——E491 forbid_3）。

## 本地复现/验证结果

- 在干净 worktree（基于 `feat/apt-pkg-2.7.14` @ 480208db5）执行 `CI_PACKAGES="archives/a/apt-pkg/2.7.14" CI_BRANCH="feat/apt-pkg-2.7.14" CI_PR_NUMBER="14901" CONAN_PROFILE=ohos-aarch64-local zsh ci/conan/build_and_test.sh`：
  - `G0_RESULT=pass`、`L0_RESULT=pass`、`conan create passed`、test_package 探针全 PASS（T1-T14）、`L1/L5_RESULT=pass`、`EXIT=0`、`All packages built and tested successfully ✅`；
  - 注意：直接跑（用 repo 内 CI profile）会因本机无 `/data/service/hnp/bin/clang` 报 `CMAKE_C_COMPILER is not a full path`——本地复现需 `CONAN_PROFILE=ohos-aarch64-local`（本机 profile 工具链路径已适配）。

## 适用范围

- 全部在共享/受限 worker 上走 CMake（`-G "Unix Makefiles"` 默认生成器）的适配，尤其 `cmake.configure()` 在编译器探测试编译（try_compile/`cmTC_*`）阶段失败且报 `resource temporarily unavailable` / `Problem parsing /proc/meminfo`；
- 同型签名还包括 `fork: Out of memory`、`can't fork - try again`、`posix_spawn: Resource temporarily unavailable`、`Bus error`（内存压力下）等间歇性基础设施失败；
- 与 meson/autotools EAGAIN 变体共享"同一 SHA 跨 worker 不一致 → 先判环境再动代码"的判据。

## 边界 / 反例

- 若失败信息是明确的可复现编译错误（`fatal error: ... file not found`、`undefined reference`、`invalid library name in -stdlib`），且同一 SHA 稳定复现，则不是本条目范畴（分别归 E455 / 具体编译错误类条目）；
- 本条目**不**为"跳过测试/伪造通过"提供借口：必须留可复核的日志与本地对照证据。
