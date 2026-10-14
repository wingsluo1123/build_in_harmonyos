# xeus 5.0.0 测试报告

- task_id: xeus-5.0.0-r01-pc3-5-20261009T094604Z
- 生成时间: 2026-10-09
- 工具链: OHOS clang 15.0.4（aarch64-unknown-linux-ohos, libc++）, CMake 4.1.2, Ninja, conan 2.29.1

## 1. 上游测试（51/51 通过，全量枚举）

完整双口径台账见 `reports/test-ledger.md`。摘要：

| 口径 | 数值 |
|---|---|
| source_declared_total | 51（5 个用户测试源文件中的独立 doctest TEST_CASE） |
| configured_executable_total | 5（ctest 注册可执行体） |
| executed_passed_total | 51（5/5 可执行体全部通过） |
| failed / uninstantiated / 未运行 | 0 / 0 / 0 |

- 全量通过率: **51/51 = 100%**
- 配置可执行集合通过率: 5/5 = 100%
- 运行命令: `ctest --output-on-failure`（cwd=build-native, LD_LIBRARY_PATH 指向构建目录），exit 0
- 枚举覆盖: 用户测试源、fixture（xmock_*）、框架依赖（doctest/2.4.11）、构建目标全部入台账

## 2. test_package 消费者验证（2/2 通过）

conan create 内置 test_package 构建并运行：

- `test_xeus_consumer`: 调用 xeus 公开 API（create_successful_reply / create_complete_reply /
  create_is_complete_reply / new_xguid / get_temp_directory_path / get_current_pid /
  xbasic_fixed_string），断言可观察 JSON 结果 → Passed 0.03s
- `test_ohos_special`: HarmonyOS 专项测试（PID > 0、临时目录可写、目录真实创建、
  GUID 非空且互异、固定字符串、哈希种子）→ Passed 0.03s

运行命令: `conan create archives/x/xeus/5.0.0 -pr=default -tf test_package`，exit 0，
100% tests passed（2/2）。

## 3. 构建产物

- 静态库: `libxeus.a`（OHOS aarch64）
- 公开头: 21 个 `include/xeus/*.hpp`
- CMake 配置: xeusConfig.cmake + FindLibUUID.cmake（下游 find_package(xeus) 可用）

## 4. 结论

上游测试全部枚举、实例化并实际运行通过；消费者与鸿蒙专项测试独立计数并全部通过。
