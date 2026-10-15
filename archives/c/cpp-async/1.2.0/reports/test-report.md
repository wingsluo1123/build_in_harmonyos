# 测试报告 — cpp-async 1.2.0

## 上游测试（R51 三步法）

### 1. 清点
上游 v1.2.0 官方测试位于 `test/`（Catch2 2.13，`program.cpp` 定义 `CATCH_CONFIG_MAIN`）：

| 测试 TU | 行数 | 覆盖 |
|---|---|---|
| test/awaitable_get_tests.cpp | 169 | awaitable_get 基础/成员/非成员 co_await 取回 |
| test/awaitable_then_tests.cpp | 337 | awaitable_then 串联与值/异常传递 |
| test/task_canceled_tests.cpp | 22 | task_canceled 异常类型 |
| test/task_completion_source_tests.cpp | 1845 | task_completion_source 完成/值/异常/取消 |
| test/task_tests.cpp | 733 | task<> 协程生命周期/可等待/移动语义 |
| test/to_future_tests.cpp | 171 | to_future 转换与成员/非成员 co_await |
| test/program.cpp | 4 | Catch2 main |

### 2. 实际运行（本机 = HarmonyOS PC 真机，aarch64，clang 15）
编译命令（应用 8 个 patches 后）：
```
clang++ -std=c++20 -fPIC -O2 -Iinclude -I<catch2/2.13.10 include> -pthread \
  test/program.cpp test/awaitable_get_tests.cpp test/awaitable_then_tests.cpp \
  test/task_canceled_tests.cpp test/task_completion_source_tests.cpp \
  test/task_tests.cpp test/to_future_tests.cpp -o upstream_tests
```
运行结果：
```
Passed all 176 test cases with 176 assertions.
```
**176/176 通过（100%）**，exit code 0。

### 3. 回填与说明
- 上游测试使用 Catch2 2.13（vcpkg.json 声明 2.13.9#1；本机以 registry 中 2.13.10 编译，API 兼容）。
- 为在 clang/C++20（OHOS 工具链）下编译，应用 8 个 patches：
  - `0001`（库头 `include/async/awaitable_resume_t.h`）：C++20 concepts 分支对非成员 `operator co_await` 的探测从 lvalue `t` 改为 `std::declval<T>()`，修复 clang 下 `co_await` 表达式的 overload resolution（上游仅 MSVC 路径正确）。
  - `0002-0008`（测试辅助头）：移除 `await_suspend` 上无效的 `constexpr`（函数体含 `assert(false)`，C++20 下 constexpr 函数体非法）。属测试代码，不影响库行为。

## test_package 消费者测试（R34）
`test_package/test.cpp` 真实调用被测库 API（非空壳）：
1. `async::awaitable_get(producer(42))` 校验 `task<int>` co_return 值 == 42；
2. `async::event_signal` 跨线程 `set()`/`wait_for()` 校验信号投递。
W3 本地 CI 模拟 L1e 破坏性反向验证通过（sabotage include/ 后构建失败，确认测试真实依赖被测包）。

## 结论
- 上游测试：176/176 通过。
- test_package：通过（conan create 内嵌执行，L1/L1e 通过）。
- 无 bin/ 产物（header-only 库），L2 smoke 跳过。

## 运行证据（R03：.log 已从交付树删除，等价文本证据保留于此）

赛事规则 R19（交付文件规范）：交付树不得包含提交的 `.log` 文件。R03 已从交付树删除 `reports/` 下 4 个 `.log`（conan-create.log、w3-local-ci.log、harmonyos-consumer-e2e-build.log、harmonyos-consumer-e2e-run.log），运行证据改为设备侧绝对路径日志 + SHA-256，等价关键结果原文保留如下：

### conan create（conan-verify G2）
- 设备侧绝对路径：`/storage/Users/currentUser/tianyi/build_in_harmonyos/.workflow/cpp-async-1.2.0/.ci_logs/conan_build_cpp-async_1.2.0.log`
- 设备侧日志 SHA-256：`73c4ed640d0c867d9327d72b4485ccea6132944ece0e6eaaab8bc64ec8acb1dc`
- 原交付态 `reports/conan-create.log` SHA-256：`e37624fd8193e7249320075e2a38db1bdac3e8fd2b6b1f7319744103e496f9f0`
- 关键结果行原文：
  ```
  1/1 Test #1: test_cpp-async ...................   Passed    0.07 sec
  100% tests passed, 0 tests failed out of 1
  ```
- 退出码：0

### W3 本地 CI 模拟（forward gate）
- 原交付态 `reports/w3-local-ci.log` SHA-256：`beeb45742168c8af1ab987e4aae4675520c10193f89c78c15fd06beb181a6ec3`
- 关键结果行原文：
  ```
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: test_package executed
  L2_RESULT=skip: no bin/ dir
  L4_RESULT=pass: patches clean
  L5_RESULT=warn: no artifacts found
  ━━━ Build Summary ━━━
    Total:   1
    Success: 1
    Failed:  0
    Pass rate: 100.0% (1/1)
  [step] All packages built and tested successfully ✅
  ```

### 鸿蒙特有测试端到端（harmonyos consumer e2e）
- 编译（原交付态 `reports/harmonyos-consumer-e2e-build.log`）SHA-256：`14693179b229cc0975a4262ab35c567183c2da408ef492212cae277122008182`
  - 关键结果：clang++ 编译 exit 0（`1 warning generated.`，仅 `jobserver mkfifo` 环境噪音，无错误）
- 运行（原交付态 `reports/harmonyos-consumer-e2e-run.log`）SHA-256：`ca9f51275c852a6ba57b0c36fb476ffde760bbf14b0fb5aaebe779bb828881c5`
  - 关键结果行原文：
    ```
    PASS[pipeline]: transform(producer(41)) == 42
    PASS[signal]: event_signal 跨线程投递成功 (produced=7)
    PASS[exception]: 协程异常正确传播并被主线程捕获
    harmonyos consumer e2e: ALL PASS (pipeline=42, signal delivered, exception propagated)
    ```
  - 真机运行 exit 0；受控失败变体验证 exit 1（证可失败、非恒绿）。
