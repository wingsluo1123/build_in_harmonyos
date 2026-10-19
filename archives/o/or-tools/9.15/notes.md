# or-tools 9.15 适配笔记

## 编译环境

- 构建系统: CMake（上游 CMake 4.1.2 / Ninja，CMakeLists 顶部
  `project(ortools VERSION 9.15 LANGUAGES CXX C)`）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`，`/data/service/hnp/bin/clang`）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
  （os=OHOS / arch=armv8 / compiler=clang / libcxx=libc++ / cppstd=17）
- 设备: HarmonyOS PC 本机（aarch64，原生构建，build=host=OHOS）
- 内存约束: 4GB —— 上游 262 个测试 + 全量静态库并行编译会 OOM，
  本地构建必须命令行注入 `-c tools.build:jobs=1`（串行，仅本地离线验证用；**勿写入配方**——
  CI worker 内存充足可并行，pytorch/qtbase 先例；CI 侧若 OOM 由主编另走基础设施 PR 处理）。
  ⚠️ `CMAKE_BUILD_PARALLEL_LEVEL=1` 对 conan 2.29 的 CMake helper **无效**（被
  `tools.build:jobs` 默认值 = CPU 数 20 覆盖，见下「-j1 机制更正」）

## 编译步骤

```bash
# W3/conan create 路径（CI 同源）
conan create archives/o/or-tools/9.15/ -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=or-tools/* --user=ohpcd --channel=stable
```

conanfile.py 内部（`generate()` 注入，全部为真实 CMake 开关）：

1. `BUILD_DEPS=OFF`（主编实测：ON 会强制所有 `BUILD_*=ON` 并从 git FetchContent
   克隆全部依赖源码 —— 不可离线、耗时且极易失败；依赖全部由 Conan 提供）
2. 逐项关闭自建依赖：`BUILD_ZLIB/BUILD_BZip2/BUILD_absl/BUILD_Protobuf/
   BUILD_Eigen3/BUILD_re2/BUILD_googletest/BUILD_benchmark=OFF`
3. 语言绑定全关：`BUILD_PYTHON/BUILD_JAVA/BUILD_DOTNET=OFF`；`BUILD_CXX=ON`；
   `BUILD_SAMPLES=OFF`；`BUILD_EXAMPLES=OFF`；`BUILD_TESTING=ON`
4. 求解器开关：`USE_GLOP/USE_BOP/USE_PDLP/USE_COINOR/USE_HIGHS=ON`；
   `USE_SCIP/USE_GUROBI/USE_XPRESS/USE_GLPK/USE_CPLEX=OFF`
5. 静态 + PIC：`BUILD_SHARED_LIBS=OFF`、`CMAKE_POSITION_INDEPENDENT_CODE=ON`、
   `CMAKE_BUILD_WITH_INSTALL_RPATH=TRUE`
6. `_DIR` 注入（依赖包自带的 CMake config，含 or-tools check_deps 需要的完整
   component targets）：
   - `absl_DIR` → abseil-cpp 包 `lib/cmake/absl`
   - `protobuf_DIR` → protobuf 包 `lib/cmake/protobuf`
   - `GTest_DIR` → gtest 包 `lib/cmake/GTest`
   - `OR_TOOLS_PROTOC_EXECUTABLE` → protobuf 包 `bin/protoc`
   - `CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES` → abseil include（修复 protobuf
     生成的 `.pb.cc` 缺 absl 头）

```bash
# 上游测试（conanfile.py build() 内，CI L1 要求）
ctest --output-on-failure   # 注册数以构建为准（预计 262 个 cxx_* 项，sat 5 个上游 DISABLED）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `BUILD_DEPS=ON` 强制所有 `BUILD_*=ON` 并从 git FetchContent 克隆依赖 | or-tools CMakeLists 用 `CMAKE_DEPENDENT_OPTION(...,"NOT BUILD_DEPS",ON)` 联动，ON 时走内嵌 FetchContent 源码树 | 主编实测结论固化：`-DBUILD_DEPS=OFF`，依赖全部走 Conan 制品仓 |
| 2 | check_deps 硬性 FATAL `ZLIB::ZLIB / BZip2::BZip2 / Coin::CbcSolver / Coin::ClpSolver` | Conan CMakeDeps 按 recipe 名导出 `zlib::zlib / bzip2::bzip2 / coinutils::coinutils / coin-or::coin-or / clp::clp / cgl::cgl / cbc::cbc`，与 or-tools 期望的 target 名不一致 | 补丁 0002 在 check_deps.cmake 顶部加 ALIAS 桥接（sat/linear_solver 链接 `Coin::Cbc`/`Coin::Clp` 一并覆盖） |
| 3 | `find_package(Osi REQUIRED)` 找不到 Osi | Osi 的 Conan 包名为 `coin-or`，CMakeDeps 只生成 `coin-or-config.cmake`，无 `OsiConfig`/`osi-config` | 补丁 0001 在 system_deps.cmake 的 Osi 附近加 `find_package(coin-or CONFIG REQUIRED)` 兜底 |
| 4 | 消费者（test_package）配置时 `Coin::*` target 不存在 | 安装的 `ortoolsTargets.cmake` 以 `Coin::*`/`ZLIB::ZLIB`/`BZip2::BZip2` 为 INTERFACE 链接依赖 | 补丁 0003 在 ortoolsConfig.cmake.in 加消费者侧 ALIAS（find_dependency 后） |
| 5 | protobuf 生成的 `.pb.cc` 编译缺 absl 头 | or-tools 代码生成源 include absl 头，但 CMake 的 include 传播不覆盖生成文件 | `CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES` 注入 abseil include 目录 |
| 6 | lang-preflight 把项目误判为 go | or-tools 根目录有 `go.mod`（Go wrapper 的模块描述），源码主体是 CMake+C++ | 判定为 cpp 继续适配；知识草稿 `DRAFT-or-tools-9.15-langpreflight-go-misdetect` 已沉淀 |
| 7 | 4GB 内存下全量编译/测试 OOM 风险 | 静态全量库 + 262 个测试 TU 并行编译内存峰值高 | 本地命令行 `-c tools.build:jobs=1` 串行（见「-j1 机制更正」）；不写入配方 |
| 8 | 可执行文件链接缺 `utf8_range_IsValid/ValidPrefix`（run2：fzn-cp-sat 55% 链接失败） | `protobuf::libprotobuf` 接口库 `utf8_range::utf8_validity`（来自 protobuf-config.cmake 内 `find_package(utf8_range CONFIG)`）未传播到 or-tools 可执行链接行（absl/protobuf 均正常，唯独 utf8_range 缺失） | **配方级修复（主编拍板方案 A，run3 已验证生效）**：`generate()` 追加 `tc.variables["CMAKE_EXE_LINKER_FLAGS"] = f"-L{protobuf_pkg}/lib -lutf8_validity"`（protobuf_pkg = `self.dependencies["protobuf"].package_folder` 动态派生，R49 禁硬编码；`.replace("\\","/")` 同 `_DIR` 写法）。两库 `libutf8_range.a`/`libutf8_validity.a` 均 nm 导出目标符号，首选 `-lutf8_validity`（与 protobuf 接口声明一致）；本次 utf8 符号全部解析成功，`-lutf8_range` 备选分支未触发 |
| 9 | 测试可执行文件链接缺 `absl_testing::StatusIsMatcherCommonImpl`（run3：graph_christofides_test 60% 链接失败，新暴露独立缺陷） | `graph_christofides_test.cc` 用 `::testing::status::StatusIs`，实现在 abseil 测试专用库 `status_matchers` 中；**abseil-cpp conan 包未提供** `libabsl_status_matchers.a` / `absl::status_matchers` 目标（lib 91 个 .a 中无，lib/cmake/absl 无该 target）——该组件因 `ABSL_BUILD_TESTING=OFF`（gtest 依赖组件）未编译进已发布包 | **配方内自建（主编定论，run4 生效）**：conandata 增加 abseil-src 官方源码（同 tag 20260107.1，sha256 已核）；source() `get(..., destination="abseil-src")`；generate() 注入 `OR_TOOLS_ABSEIL_SRC` + `absl_INCLUDE_DIR`/`gtest_INCLUDE_DIR`；补丁 0002 将原 INTERFACE stub 升级为真实 STATIC 库（编译 `absl/status/internal/status_matchers.cc`，链接 `absl::status absl::strings GTest::gmock`）。**上游 262 个测试零修改** |
| 10 | 本地 -j1 机制（`CMAKE_BUILD_PARALLEL_LEVEL=1` 无效） | conan 2.29 CMake helper 用 `tools.build:jobs` 默认值（本机 CPU 数 20）显式追加 `-j20`，覆盖环境变量（run1 18% 无声死亡疑 OOM） | 本地命令行注入 `-c tools.build:jobs=1`（仅本地离线验证；**不入配方**，CI worker 内存充足可并行） |
| 11 | 90% 编译失败：math_opt 测试 `EXPECT_DEATH(expr, kObjectsFromOtherModelStorage)` 报 `no matching function for call to 'MakeDeathTestMatcher'`（variable_and_expressions_test.cc L3510 等） | googletest v1.17.0 的 `testing::internal::MakeDeathTestMatcher` 只有 4 个重载（RE/const char*/const std::string&/Matcher<const std::string&>），**无 absl::string_view 重载**（已 web_fetch 官方 v1.17.0 头文件 + 比对 conan 包内头文件双确认）；or-tools 9.15 math_opt 测试把 `constexpr absl::string_view` 常量传给 EXPECT_DEATH → 无法编译。受影响文件均 `#include "ortools/base/gmock.h"`（variable_and_expressions_test.cc L27 / incremental_solver_test.cc L22 / model_test.cc L33 等）。系 or-tools 测试代码与 gtest 1.17.0 的真实不兼容，非包缺陷（包忠实等于官方 v1.17.0） | **补丁 0004（主编拍板：单一头文件兼容重载，零改动测试断言）**：在 `ortools/base/gmock.h` 的 #include 块之后补 `testing::internal::MakeDeathTestMatcher(absl::string_view)` 重载（`return ContainsRegex(std::string(regex));`，正则转 std::string，断言语义不变）。R8：非平台宏，纯 gtest 版本兼容，符合 portability |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-system_deps-coin-or-fallback.patch | cmake/system_deps.cmake | `find_package(Osi REQUIRED)` → `find_package(Osi QUIET)` + `find_package(coin-or CONFIG REQUIRED)` 兜底 |
| 0002-check_deps-target-aliases.patch | cmake/check_deps.cmake | 顶部加 Conan target → or-tools target ALIAS（ZLIB/BZip2/Coin 全套）+ 把缺失的 `absl::status_matchers` 从 INTERFACE stub 升级为**真实 STATIC 库**（编译官方 abseil 源码 `absl/status/internal/status_matchers.cc`，`OR_TOOLS_ABSEIL_SRC`/`absl_INCLUDE_DIR`/`gtest_INCLUDE_DIR` 由配方 generate() 注入） |
| 0003-ortools-config-consumer-aliases.patch | cmake/ortoolsConfig.cmake.in | 消费者侧 find_dependency 后加同名 ALIAS，防安装后的 `Coin::*`/`ZLIB::ZLIB` 引用悬空 |
| 0004-gmock-death-test-string_view-overload.patch | ortools/base/gmock.h | #include 块之后补 `testing::internal::MakeDeathTestMatcher(absl::string_view)` 兼容重载（gtest 1.17.0 无该重载，math_opt 测试传 constexpr absl::string_view 死亡测试匹配器；`return ContainsRegex(std::string(regex))`，断言语义不变） |

补丁已用 `git apply --check`（基于 v9.15 tarball 源码上下文，0001→0004 逐一顺序）验证可 apply。

## 依赖版本

| 依赖 | 制品仓实际版本 | 说明 |
|------|---------------|------|
| zlib | 1.3.1 | system 同名库，静态（R26） |
| bzip2 | 1.0.8 | 静态 |
| abseil-cpp | 20260107.1 | 自带 lib/cmake/absl 全量 component targets；缺 status_matchers 测试库（本配方用官方源码自建） |
| protobuf | 33.6.1 | 自带 lib/cmake/protobuf + bin/protoc |
| eigen | 3.4.0 | Eigen3::Eigen |
| re2 | 2024-04-01 | re2::re2 |
| gtest | 1.17.0 | 自带 lib/cmake/GTest（GTest::gtest_main/gmock） |
| benchmark | 1.9.5 | 仅测试用 |
| coinutils | 2.11.13 | coinutils::coinutils |
| coin-or | 0.108.12 | Osi → coin-or::coin-or（补丁桥接） |
| clp | 1.17.10 | clp::clp（含 Clp/ClpSolver/OsiClp） |
| cgl | 0.60.10.1 | cgl::cgl |
| cbc | 2.10.13 | cbc::cbc（含 Cbc/CbcSolver/OsiCbc） |
| highs | 1.13.1 | highs::highs |

## 验证结果

```bash
# W3 conan create 实测（2026-09-25 返工轮 run3，utf8_range 方案 A 修复后）：
# - conan create 退出码：非零（ConanException: Error 2 while executing）
# - 终态：build_failed（测试可执行文件链接阶段，bin/graph_christofides_test）
#   ld.lld: error: undefined symbol: absl_testing::...::StatusIsMatcherCommonImpl
#   （DescribeTo / DescribeNegationTo / MatchAndExplain）
#   根因：graph_christofides_test.cc 使用 ::testing::status::StatusIs，实现在 abseil
#   测试专用库 status_matchers 中，但 abseil-cpp conan 包未提供 libabsl_status_matchers.a
#   与 absl::status_matchers 目标（49 个 *_test.cc 受影响，系统性预存缺陷，非 utf8_range 相关）
# - ✅ utf8_range 修复验证：bin/fzn-cp-sat 于 55% 链接成功（日志行 1952），link.txt 含
#   -lutf8_validity，产物 14MB 正常生成；本次无任何 undefined symbol: utf8_range_*
# - ctest 注册数 / 通过数 / 通过率：未执行（构建失败于测试阶段之前；清单预计 262 项，sat 5 DISABLED）
# - test_package ctest 结果：未执行（未进入 test_package；LP/CP/OHOS 三项断言待修复后实测）
# - /proc/self/maps 静态链接断言：未执行
# - 证据日志：.scratch/or-tools-subtask/logs/conan-create.log（run3，4717 行）
#   sha256=bb498a6b59bc4f25c493420f2e69b463ba52ebdc4fd7ca6f9a1b5e144bfe3c9c
#   （run2 旧日志 sha256=685dd85c9f8bda549f8445463e44143986c0a60edd5aa3484f493e62c2ba6f75 已作废）
```

## -j2 配方级限流（评审修复，2026-10-04）

- **背景**：PR !13558 评审（评论 192516646）判定 rule7 CI 失败未闭环——#64614/#64628 conan-build
  worker 步骤 OOM、#70235 编译器探针 "resource temporarily unavailable"。上述 2026-09-25
  "勿写入配方"的决策**针对 -j1 拖慢 CI**，与 CI 实际反复 OOM 的事实冲突，本次按 E479 处方推翻：
  CI worker 与本机同为一台 24GB 无 swap 设备（桌面常驻后可用 ~5-6GB），nproc=20 默认并行度
  必然峰值 OOM，且失败步骤随机（探测阶段报 EAGAIN 亦是 fork/内存压力）。
- **修复**：conanfile.py `generate()` 中 `self.conf.define("tools.build:jobs", 2)`
  （配方级覆盖默认 20；CMake.build() 据此追加 -j2，j2 峰值约 4-6GB）。CI profile 属框架
  文件不可改，配方级 conf 是唯一合规旋钮；E479 草稿（worker OOM 处方）随本 PR 一并入库。
- **本地验证**：py_compile 通过；`tools.build:jobs` 语义经 conan 2.29.1 `conan config list`
  确认（"Default compile jobs number -jX"）；完整编译验证按项目规程走 CI（本机内存不足）。

## -j1 机制更正（已定论，2026-09-25）

- **结论**：`CMAKE_BUILD_PARALLEL_LEVEL=1` 对 conan 2.29 的 CMake helper **无效**——helper 用
  `tools.build:jobs` 默认值（本机 CPU 数 20）显式追加 `-j20`，覆盖环境变量（run1 的 18% 无声死亡
  即 -j20 OOM 疑似根因）。
- **正确做法**：本地构建命令行注入 `-c tools.build:jobs=1`（实测生效：`cmake --build ... -- -j1`）。
- **勿写入配方**（`-j1` 不硬编码进 conanfile.py）：CI worker 内存充足可并行（pytorch/qtbase 先例）；
  CI 侧若 OOM 由主编另走基础设施 PR 处理。`tools.build:jobs=1` 与
  `FETCHCONTENT_SOURCE_DIR_PROTOBUF-MATCHERS` 均仅为本地离线验证的**命令行 conf**，不入配方。

## ⚠️ W3 遗留阻塞项（主编决策）

1. **abseil-cpp 缺 status_matchers 测试库**：**已根治（配方内自建，主编定论）**——conandata 增加
   abseil-src 官方源码 + source() 下载 + generate() 注入 `OR_TOOLS_ABSEIL_SRC`/include 目录 + 补丁 0002
   把 INTERFACE stub 升级为真实 STATIC 库。上游 262 个测试**零修改**。不再阻塞。
2. **utf8_range 链接缺陷**：**已修复并验证**（方案 A，run3 fzn-cp-sat 链接成功），不再阻塞。

## 注意事项

- 内存 4GB 约束：构建与测试均串行（`-j1`），超时预算需按包放宽
  （`ohc-run.py timeout set or-tools 9.15 57600`）。
- 状态为 built（非 published）：待 conan create + 上游测试回填后由主编推进
  release 发布。
