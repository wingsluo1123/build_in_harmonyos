# hpx 1.11.0 测试报告（R51 / R53）

> 环境：HarmonyOS PC（aarch64 / OHOS 6.0 / clang 15 / libc++ / C++17）。
> 构建与运行均通过 Conan（ohpcd 依赖链）在 HarmonyOS PC 上完成。
> W3 本地 CI 结果：`.ci-result.json`（exit_code=0，log_sha256=`8c3b95d493218533e3bdaf66dbc35ea9bc620637a97c0dd379dd97676c208498`）。

## 一、上游测试清点（R51 第一步）

| 项 | 数值 | 方法 |
|---|---|---|
| 含 tests/ 的 CMakeLists（测试注册目录） | 516 | 源码树扫描（HPX 1.11.0 官方 tarball） |
| CTest 注册条目（`set(tests ...)` 展开，近似） | ~1180 | 解析各 tests/CMakeLists.txt |
| 测试源文件（tests/ 下 `*.cpp`） | 1303 | 源码树扫描 |
| 测试框架 | 上游 `HPX_TEST` 宏 + CTest；含分布式/多进程/依赖外部服务类用例 |

## 二、实测子集（R51 第二步：HarmonyOS PC 实际运行）

选取与本次适配直接相关的模块（协程上下文切换 / 线程 / 同步 / futures / 异步组合子 /
运行时初始化），对 **W3 打包产物**（`hpx/1.11.0:95a7c017f93c998ef1e8408c51923142c0247af7#e0bba358...`）
编译并运行 18 个上游用例：

| # | 用例（上游源码路径） | 结果 |
|---|---|---|
| 1 | libs/core/coroutines/tests/regressions/coroutine_function_destructor_yield_4800.cpp | PASS 0.10s |
| 2 | libs/core/threading_base/tests/regressions/thread_local_data.cpp | PASS 0.06s |
| 3 | libs/core/threading_base/tests/regressions/thread_stacksize_current.cpp | PASS 0.13s |
| 4 | libs/core/threading/tests/unit/condition_variable2.cpp | PASS 14.72s |
| 5 | libs/core/threading/tests/unit/condition_variable3.cpp | PASS 0.26s |
| 6 | libs/core/threading/tests/unit/jthread1.cpp | PASS 4.56s |
| 7 | libs/core/threading/tests/unit/jthread2.cpp | PASS 6.31s |
| 8 | libs/core/synchronization/tests/regressions/ignore_while_locked_1485.cpp | PASS 0.06s |
| 9 | libs/core/synchronization/tests/regressions/shared_mutex_1702.cpp | PASS 0.06s |
| 10 | libs/core/synchronization/tests/unit/async_rw_mutex.cpp | PASS 0.19s |
| 11 | libs/core/lcos_local/tests/regressions/safely_destroy_promise_1481.cpp | PASS 0.18s |
| 12 | libs/core/lcos_local/tests/unit/local_dataflow.cpp | PASS 0.07s |
| 13 | libs/core/futures/tests/regressions/future_790.cpp | PASS 0.06s |
| 14 | libs/core/async_combinators/tests/unit/wait_all.cpp | PASS 1.12s |
| 15 | libs/core/init_runtime_local/tests/unit/on_finalize.cpp | PASS 0.06s |
| 16 | libs/core/runtime_local/tests/unit/thread_mapper.cpp | PASS 0.08s |
| 17 | libs/core/schedulers/tests/unit/schedule_last.cpp | PASS 0.06s |
| 18 | libs/core/executors/tests/regressions/pu_count_6184.cpp | PASS 0.05s |

**结果：N′ = 18，通过 18，失败 0 —— 通过率 100%**（ctest: `100% tests passed, 0 tests failed out of 18`，
总耗时 14.82s；完整日志：PC `~/tmp/hpx-upstream-tests.log`）。

Harness 说明：测试可执行文件由 PC 上的小型 CMake 工程编译（`find_package(HPX)` 使用
W3 产物的 Conan 配置），运行时加载 conanrun 环境（LD_LIBRARY_PATH 含包与全部传递依赖）。
`hpx_testing` 支持模块在 Makefiles 生成器下按上游设计以 OBJECT 方式内联、不单独归档，
harness 从源码树编译该两个源文件作为测试链接支持（被测 HPX 库本体为打包产物，未改动）。

## 三、未执行用例说明（R51 第二步：逐类技术原因）

完整套件（~1300 个测试源文件 / ~1180 条 CTest 注册）未整体执行，按类归因：

1. **规模/预算**：模板重型 C++ 用例的完整构建+运行远超 W3/CI 预算（本包 10800s 预算
   已用于库本体构建与消费者测试；完整套件在上游 CI 亦分组并行数小时）。
2. **分布式/多节点类**：依赖多进程/多节点环境（TCP parcelport、AGAS 服务等），
   单机 CI worker 条件不满足。
3. **可选后端类**：CUDA/HIP/OpenMP/MPI/Valgrind/APEX/PAPI 等后端在 OHOS 适配中
   关闭（平台限制），相应用例不适用。
4. **性能基准类**：`tests/performance` 为基准测量而非正确性测试，不纳入适配验证。

## 四、鸿蒙特有测试（R53）

`test_package/test_hpx.cpp`（消费者端到端；W3 内实际构建并运行，见
`reports/w3-local-ci.log` 第 5827-5834 行）——**7/7 断言通过**
（`RESULT: 7 checks, 0 failures`）：

1. HPX runtime 以 ≥2 worker 线程启动（ucontext/libucontext 协程后端端到端）
2. HPX 运行 ≥2 OS 线程
3. 硬件并发数 ≥1（hwloc 拓扑发现可用）
4. 64 个 `hpx::async` 任务返回正确结果
5. future continuation 链正确
6. promise + `hpx::thread` 挂起/恢复（协程上下文切换路径）
7. 消费者可执行文件为 AArch64 ELF（OHOS 目标）

## 五、证据索引

| 证据 | 位置 |
|---|---|
| W3 本地 CI（exit_code=0 + 日志哈希） | `archives/h/hpx/1.11.0/.ci-result.json` |
| W3 完整日志（含 test_package 实跑） | `archives/h/hpx/1.11.0/reports/w3-local-ci.log` |
| G2 conan create 日志 | `archives/h/hpx/1.11.0/reports/conan-create.log` |
| 配方验证报告（G0-G4/L2/L4/L5） | `archives/h/hpx/1.11.0/reports/conan-verify-report.md` |
| 上游测试运行日志（PC） | `~/tmp/hpx-upstream-tests.log` |
| 打包产物（conan cache 导出） | `archives/h/hpx/1.11.0/packaging/hpx-1.11.0.tar.gz`（58MB，不入 PR） |
| 共享库签名 | 包内 `lib/**/*.so*` 均含有效 `.codesign`（binary-sign-tool selfSign） |
