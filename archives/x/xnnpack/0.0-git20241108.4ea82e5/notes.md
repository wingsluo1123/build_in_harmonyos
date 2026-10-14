# xnnpack 0.0-git20241108.4ea82e5 适配笔记

## 编译环境
- 构建系统: cmake（上游纯 CMake；本配方用 `cmake_layout(src_folder="src", build_folder="build_dir")`）
- 编译日期: 2026-10-06
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`）
- 目标平台: OpenHarmony PC aarch64（conan profile `ci/conan/profiles/ohos-aarch64`，os=OHOS / arch=armv8）
- 状态: built

## 上游快照与版本号
- 上游仓库: https://github.com/google/XNNPACK
- commit: `4ea82e595b36106653175dcb04b2aa532660d0d8`（2024-11-08T14:56:11-08:00，"Cast to float to avoid compile error"）
- tarball sha256: `3ef066f2f9b8ac474cd3fd606c601a30bbab59a56406c69019610339f02b6032`（8923022 bytes）
- 版本号 `0.0-git20241108.4ea82e5` = 上游无 release tag 时的仓库惯例（同
  `archives/c/cpuinfo`、`archives/r/ruy`、`archives/a/asmjit`），日期段与 commit
  日期逐字对应；平台任务（rawId 12165）的权威 version 与此一致。

## 编译步骤
```sh
conan create archives/x/xnnpack/0.0-git20241108.4ea82e5 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
```
配方内部：`CMakeToolchain` + `CMakeDeps` → configure → build → `ctest -V`
（上游测试在 `build()` 内真实执行）→ install → `package()`。
configure/build/ctest 三步的输出绑定到 `build_dir/logs/<step>.log` 再回显（见"注意事项"）。

## 依赖处理（本包的关键适配点）
| 依赖 | 处理方式 | 依据 |
|---|---|---|
| cpuinfo | conan 包 `cpuinfo/0.0-git20250905.877328f` | 制品仓已有 OHOS 适配版；其 `cmake_target_name=cpuinfo::cpuinfo` |
| fxdiv | conan 包 `fxdiv/0.0-git63058eff77` | header-only；XNNPACK 与 pthreadpool 共用 |
| **pthreadpool** | **vendor 源码，`add_subdirectory` 构建为静态库** | 制品仓 `conan list -r=ohpcd pthreadpool/*` 实测 0 命中、`archives/` 全树无此包；而 `include/xnnpack.h` 直接 `#include "pthreadpool.h"`、CMake 对它做 `TARGET_LINK_LIBRARIES(XNNPACK PUBLIC pthreadpool)` ⇒ 硬依赖。版本锁定在上游 `cmake/DownloadPThreadPool.cmake` 的同一 revision `4fe0e1e1…`（sha256 `a4cf06de…`） |
| KleidiAI | **关闭**（`XNNPACK_ENABLE_KLEIDIAI=OFF`） | 上游 arm64 默认 ON，但源码只从 `gitlab.arm.com` 取（CI 的镜像 fallback 只覆盖 github.com）。它是可选第三方 GEMM 加速层，XNNPACK 自带的 NEON/NEONDOT/NEONI8MM/NEONFP16ARITH 微内核与运行期 CPU 分派不受影响 |
| googletest | vendor **上游钉的同一 revision**（`df1544bcee0c…` = 1.15.2，sha256 `4f45c221…`） | XNNPACK 的 `cmake/DownloadGoogleTest.cmake` 就钉这个 revision ⇒ 与上游 CI 同源。三个 `CMakeLists` 都声明 `cmake_minimum_required(VERSION 3.13)`，CMake 4.1.2 可 configure。**不要用 v1.14.0**（cpuinfo/ruy 用的是它）：1.14.0 的 `DoubleNearPredFormat` 没有同号无穷短路分支，`ASSERT_NEAR(-inf,-inf,tol)` 算成 NaN 判失败（实测 594 条断言假失败、5 个 ctest 二进制变红）。**`BUILD_GMOCK` 必须保持 ON**（XNNPACK 的 `*-test` 目标显式链接 `GTest::gmock`） |
| fp16 | 不引入 | 本快照的 XNNPACK 自带 `src/xnnpack/fp16.h` 摘录，CMake 无 fp16 target（CCI 配方要求 fp16 是历史原因） |

配置期依赖下载的抑制机制：XNNPACK 的依赖判定统一写成 `IF(NOT TARGET <dep>)`，
所以在 `project()` 结束前把同名 target 建好即整段跳过；再配合
`XNNPACK_USE_SYSTEM_LIBS=ON` 压掉顶部那块 ExternalProject 配置期下载。
落地文件 `xnnpack_project_include.cmake`，经标准 CMake 变量
`CMAKE_PROJECT_XNNPACK_INCLUDE` 注入。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `FATAL_ERROR "Unrecognized CMAKE_SYSTEM_NAME"`（aarch64 微内核分派会全部走空） | OHOS profile 下 Conan 给 `CMAKE_SYSTEM_NAME=HarmonyOS`，不在上游白名单 `^(Android\|Darwin\|iOS\|Linux\|Windows\|CYGWIN\|MSYS\|QURT)$` 内 | `generate()` 里同时用 `tc.variables` 与 `tc.cache_variables` 钉 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`（同 `archives/r/ruy`、`archives/c/cpuinfo`）；实测 configure 打出 `-- Building for XNNPACK_TARGET_PROCESSOR: arm64` |
| 2 | configure 阶段 `Target "f32-vtanh-test" links to: GTest::gmock but the target was not found` | vendored googletest 被设成 `BUILD_GMOCK=OFF`（照搬 ruy 做法，但 XNNPACK 的测试确实用 gmock） | 去掉 `BUILD_GMOCK=OFF`，保持 googletest 默认 ON |
| 3 | 构建到 37% 时 `Error 2`，日志尾 `/bin/sh: can't fork - try again` | 共享设备上的进程创建被拒（notes/device-facts.md §一.5/§一.9：`MemFree` 尚有余量时 fork 仍会 EAGAIN），不是配方缺陷 | 把 `tools.build:jobs` 从 affinity 数降到 `min(affinity, 6)`；本次续跑再叠加 `taskset -c 0-5`（见"注意事项"第 2 条：CLI `-c` 覆盖无效） |
| 4 | prescan 报 critical `PSCAN-MUSL-002`「mremap 在 OHOS 上不可用」 | 该规则是 musl 的通用判断；OHOS sysroot 实测 `<sys/mman.h>` 在 `_GNU_SOURCE` 下**声明了 `mremap`**（`void *mremap (void *, size_t, size_t, int, ...)`）与 `MREMAP_MAYMOVE` | 复核为**误报**；`src/memory.c` 的调用位于 `#if XNN_PLATFORM_LINUX` 分支，链接/运行结果见验证结果 |
| 5 | prescan 报 high/medium「`#!/bin/bash` 硬编码」（4 个脚本） | OHOS 无 `/bin/bash`（bash 在 `/data/service/hnp/bin/bash`） | 这 4 个脚本（2 个 hexagon 运行脚本、`scripts/generate-qs8-f16-vcvt.sh`、`test/microkernel_lists_test.sh`）**未被 CMakeLists/ctest 引用**，不在构建与测试面内；未改上游文件 |
| 6 | `ctest` 里 5 个二进制变红、116 条用例失败，其中 594 条断言报 `The difference between y[i] and y_ref[i] is nan`（两侧都是 `-inf`） | vendor 的 googletest **v1.14.0** 的 `DoubleNearPredFormat` 没有「同号无穷直接判成功」的短路分支：`fabs(-inf - -inf)` = NaN ⇒ `NaN <= abs_error` 为假。XNNPACK 的 f16/f32 微内核测试在饱和输入上确实会产出同号 ±inf（如 f16 vlrelu 的 `-52096 * slope` 溢出成 `-inf`），上游钉的 1.15.2 有该分支、所以上游 CI 看不到 | 把 vendor 的 googletest 换回**上游钉的同一 revision**（`df1544bcee0c…` = 1.15.2）；实测 `gtest.cc:1676-1680` 有 `if (std::isinf(val1) && std::isinf(val2) && signbit 相同…) return AssertionSuccess();` |
| 7 | `f32-vgelu-test` 另有 73 条**真实数值**断言失败（`y=-1.672e-06` vs `y_ref=-0`，容差 `10*FLT_EPSILON=1.192e-06`） | `src/xnnpack/simd/f32-scalar.h` 把 `xnn_fmadd_f32(a,b,c)` 写成 `(a*b)+c`，而该头**不定义** `XNN_SIMD_HAS_NATIVE_FMA`（只有 neon/avx2/fma3 等架构头定义）⇒ 标量有理微内核走"未启用 FMA"分支（`vmax_abs_x=5.1158981323`，注释写明该值是插值恰好返回 ±1.0f 的第一个浮点数）。aarch64 上 clang 默认 `-ffp-contract=on` 把 `(a*b)+c` 收缩成 `fmadd` ⇒ 算术是 FMA、标定是非 FMA，clamp 点残余 ~3.6e-7 被 `0.5*|x|` 放大后超容差。x86/SSE2 基线无 FMA 指令不会收缩 | 在 `xnnpack_project_include.cmake` 对 C/CXX 加 `-ffp-contract=off`（关闭表达式收缩，让"未启用 FMA 的标定"与实际算术一致；NEON 等真 FMA intrinsic 不受影响）。单文件重编验证：同一二进制由失败变 **66/66 通过** |

## 源码修改
无补丁（`patches: {}`）。全部适配都在配方内完成：上游源码树逐字节未改，
`patches/` 为空，因此不存在「补丁挟带平台宏」的问题。

配方里仍按本仓库 7879 份配方的统一骨架保留了补丁通道：
`def export_sources(self): export_conandata_patches(self)` +
`source()` 内的 `apply_conandata_patches(self)`。`patches: {}` 时两者都是
no-op（conan 的 `patches.get(self.version, [])` 取到空列表），
`conan export` 实测只导出 conandata.yml/conanfile.py/钩子三个文件、无补丁件。

## 依赖版本
- `cpuinfo/0.0-git20250905.877328f`
- `fxdiv/0.0-git63058eff77`
- vendor: pthreadpool `4fe0e1e183925bf8cfa6aae24237e724a96479b8`、googletest `df1544bcee0c7ce35cd5ea0b3eb8cc81855a4140`（= 1.15.2，上游 `cmake/DownloadGoogleTest.cmake` 钉的同一 revision）

## 验证结果
设备实测（2026-10-06，`conan create` 内嵌 `ctest -V`；由配方打印的
`HMBS_UPSTREAM_TEST_RESULT` 标记自证，四条分项满足
`TOTAL = PASS + FAIL + SKIP + NOT_RUN`）：

- N（框架注册数，255 个 gtest 二进制 `--gtest_list_tests` 求和）= 62121
- N′（本次实际运行数）= 62118；PASS = 59822、FAIL = 0、SKIP = 2296、NOT_RUN = 3
- `ctest`：`100% tests passed, 0 tests failed out of 399`（265.49 s）
- NOT_RUN 3 = 上游自带 `DISABLED_FULLY_CONNECTED_NC_QP8_F32_QC4W.*` 三条
  （gtest 列出但不执行）；SKIP 2296 = 上游 `test/` 下 790 处 `GTEST_SKIP()`
  能力守卫（如 qp8-f32-qc4w GEMM 配置本机不可用、F16 不支持等）
- `test_package`：消费者程序真实运行，自报
  `HMBS_TEST_PACKAGE_RESULT={"checks":1676,"failures":0}` → `test_xnnpack PASSED: 1676 checks`

详细报告见 `reports/conan-verify-report.md`（采信轮产出）与 PR 正文。

## 注意事项
1. **构建输出必须绑定日志文件**：OHOS 上 conan 的构建子进程若继承 recipe 进程的
   输出流，clang 会在第一个翻译单元静默退出（make 只报 `Error 1`、零诊断）。
   本配方 configure/build/ctest 三步都写 `logs/<step>.log` 再回显。
2. **并行度**：conan 默认取 `os.cpu_count()`，配方显式钉
   `tools.build:jobs = min(sched_getaffinity, 6)`。**注意 `-c tools.build:jobs=N`
   覆盖不了它**——`build()` 里的 `self.conf.define()` 会无条件覆盖调用方传入的
   conf 值（Conan 2.29 的 `Conf.define` 直接写 `_values`，实测）。要压更低只能
   `taskset -c 0-5 conan create …`（本次续跑即用 4~6 核自限，避开共享设备在
   37% 处的 `can't fork`）。
   **另注**：conan 的 build 目录哈希含 recipe revision —— 只要
   `conanfile.py`/`conandata.yml`/`exports` 有任一字节变化就会换
   `p/b/<hash>` 目录、已编译的 `.o` 全部作废（本任务三次 create 得到三个不同
   build 目录）。"同一 recipe revision 重跑即增量续建"只在文件逐字节不变时成立。
3. **`Python_EXECUTABLE` 显式钉死**：上游 `find_package(Python)` 失败时写的是
   `SET(PYTHON_EXECUTABLE "python3")`（少一个 n），而随后真正执行的是
   `${Python_EXECUTABLE}` ⇒ 空命令 ⇒ `Failed to generate "microkernels.cmake"`。
   配方用 `sys.executable` 预置该 cache 变量，避免 worker 与设备 PATH 差异踩到。
4. **pthreadpool 头是公开交付物**：`include/xnnpack.h` 直接 include `pthreadpool.h`，
   `package()` 显式把 `third_party_src/pthreadpool/include/pthreadpool.h` 装进
   `include/`（pthreadpool 自己的 `INSTALL(FILES …)` 通常已装好，这里是兜底）。
5. 本包为静态库（`shared=False`，仓库模板默认值）：包内交付
   `libXNNPACK.a` + `libmicrokernels-prod.a` + `libpthreadpool.a`，三者与
   `cpuinfo`/`fxdiv` 的链接顺序由 `package_info()` 的组件 `requires` 拓扑保证。
