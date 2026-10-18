# ISPC

[ISPC](https://ispc.github.io)（Intel Implicit SPMD Program Compiler）是一个编译器：自带 SPMD 语言
前端（用 Clang 前端库做预处理）+ LLVM 后端，把 SPMD 程序编译为 aarch64/NEON（或 x86 SSE/AVX）向量代码。

- 上游：https://github.com/ispc/ispc
- 许可证：BSD-3-Clause
- 构建系统：CMake + Ninja（Release）

## 鸿蒙 PC 适配要点

- **依赖**：ISPC 1.28.2 的 `CMakeLists.txt` 无条件链接 Clang 前端库
  （`clangFrontend clangBasic clangEdit clangLex clangSupport clangASTMatchers`），源码直接
  `#include <clang/...>` ⇒ 只带 LLVM 的包无法构建。支持区间 LLVM **18.1–21.1**。
  本包消费 `llvm-project/20.1.8`（`llvm-config --targets-built` = `AArch64 ARM X86`）。
- **平台**：设备 `uname -s = HarmonyOS` 且 CMake 无 `Platform/HarmonyOS.cmake`，配方在 `build()` 中
  生成 `include(Platform/Linux)` 的 stub；保持 native 构建（不设 `CMAKE_SYSTEM_NAME`）。
- **补丁**：`0001-host-libcxx-verbose-abort-noexcept.patch` —— `std::__libcpp_verbose_abort` 的
  `noexcept` 规格改为跟随**宿主 libc++** 版本（libc++ ≥ 20 有、OHOS SDK 的 15.0.4 没有），
  避免 `exception specification in declaration does not match previous declaration`。
- **关键配置**：`-DISPC_STATIC_LINK=OFF`（否则可执行文件静态链入 libc++ 与 `libLLVM.so` 动态链接的
  `libc++_shared.so` 冲突，`ispc --version` 即 `std::bad_cast`）；`-DCLANGPP_EXECUTABLE=<wrapper>`
  （给上游 builtins-c++ 编译补宿主 C 头目录，避免静默产出空位码 ⇒ `undefined symbol: __do_print`）。
- **签名**：产物 `bin/` 与 `lib/*.so` 在 `package()` 中统一重签 `.codesign`（OHOS 要求）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.28.2 | built | 设备验证完成：`conan create` + `test_package` + 上游两套件（PASS 2113 / FAIL 3 / SKIP 107 / NOT_RUN 0，通过率 95.05%） |

## 上游测试

| 套件 | 命令 | 用例数 | 实测 |
|------|------|--------|------|
| lit（`check-all`） | `cmake --build <build> --target check-all` | 647（639 `.ispc` + 5 `.ll` + 3 `.cpp`） | PASS 546 / FAIL 3 / SKIP 98 |
| func-tests | `cd <src> && ISPC_HOME=<build>/bin python3 scripts/run_tests.py -t neon-i32x4 -a aarch64 -o O2 -c clang++` | 1576（`tests/func-tests/*.ispc`） | PASS 1567 / FAIL 0 / SKIP 9 |

候选最大上游总数 **N = 2223**；计数口径 `TOTAL = PASS + FAIL + SKIP + NOT_RUN`，lit 的
`Unsupported` 与 `Expectedly Failed` 计入 SKIP。3 个 FAIL 均为上游测试的 host=x86 假设
（`math-lib-value.ispc` / `2780-1.ispc` / `3571.ispc`）；lit 另有 8 个 `REQUIRES: LINUX_HOST`
用例因 conan buildenv 选中的 OHOS python 使 `platform.system()` 返回 `HarmonyOS` 而判 UNSUPPORTED。
逐条原因见 `1.28.2/notes.md` §6。逐用例归类脚本见任务证据目录 `testlists/classify.py`。
