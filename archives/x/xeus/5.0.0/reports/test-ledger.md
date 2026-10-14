# xeus 5.0.0 上游测试双口径台账

- task_id: xeus-5.0.0-r01-pc3-5-20261009T094604Z
- 生成时间: 2026-10-09
- 构建目录: /storage/Users/currentUser/tmp/builds/xeus-5.0.0.work/build-native
- 工具链: OHOS clang 15.0.4 (aarch64-unknown-linux-ohos, libc++), Ninja, ctest
- 依赖: doctest/2.4.11, nlohmann_json/3.12.0, libuuid/2.42.2 (ohpcd registry)

## 统计口径（双口径）

| 口径 | 数值 |
|---|---|
| source_declared_total（源码声明独立 TEST_CASE 总数） | 51 |
| configured_executable_total（当前配置实例化/注册独立可执行用例数） | 5 |
| executed_passed_total（实际执行并通过） | 51（5/5 可执行体，内部 51 用例全过） |
| failed | 0 |
| uninstantiated / 未运行 | 0 |

- 全量通过率（源码声明口径）: 51/51 = 100%
- 当前配置可执行集合通过率: 5/5 = 100%（ctest 实测）

## 独立上游用例枚举（用户测试源）

| 源文件 | TEST_CASE 数 | 是否独立上游用例 | 分类理由 |
|---|---|---|---|
| test/test_unit_kernel.cpp | 8 | 是 | 真实 doctest TEST_CASE（get_start_message/extract_filename/should_print_version/get_username/temp_directory_path/create_directory/get_current_pid/get_tmp_hash_seed） |
| test/test_xbasic_fixed_string.cpp | 36 | 是 | 真实 doctest TEST_CASE（constructors…find 等 xbasic_fixed_string 行为用例） |
| test/test_xhash.cpp | 2 | 是 | 真实 doctest TEST_CASE（verification/sanity） |
| test/test_xin_memory_history_manager.cpp | 3 | 是 | 真实 doctest TEST_CASE（get_tail/get_range/search） |
| test/test_xsystem.cpp | 2 | 是 | 真实 doctest TEST_CASE（executable_path/prefix_path） |
| test/test_main.cpp | 0 | 否 | doctest 驱动（DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN），非用例 |

合计 51 个独立 TEST_CASE；全树 grep 确认无 TEST_CASE_TEMPLATE/TEST_CASE_F/SCENARIO 等宏前缀误计。

## 非独立入口台账（框架/样例/基准/fixture/脚本/构建目标）

| 入口 | 分类 | 是否独立用例 | 说明 |
|---|---|---|---|
| test/xmock_interpreter.cpp/.hpp | fixture | 否 | mock 解释器支撑类，非用例 |
| test/xmock_server.cpp/.hpp | fixture | 否 | mock 服务器支撑类，非用例 |
| docs/（Doxyfile/Makefile/source/） | 文档 | 否 | 仅文档，无测试 |
| .github/workflows/main.yml | CI 脚本 | 否 | 上游 CI 编排，非测试入口 |
| doctest/2.4.11 | 框架依赖 | 否 | 外部测试框架（ohpcd 制品仓） |
| CMake 目标: libxeus (shared) | 构建目标 | 否 | 被测库本体 |
| CMake 目标: test_xbasic_fixed_string / test_xhash / test_xin_memory_history_manager / test_xsystem / test_unit_kernel | 构建目标+ctest 注册 | 是（5 个可执行体） | test/CMakeLists.txt add_test 注册 |

## 构建与执行证据（命令/cwd/退出码）

- 配置: `cmake -S . -B build-native -G Ninja -DCMAKE_TOOLCHAIN_FILE=<od>/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release -DXEUS_BUILD_TESTS=ON -DXEUS_BUILD_SHARED_LIBS=ON -DXEUS_BUILD_STATIC_LIBS=OFF`，cwd=/storage/Users/currentUser/tmp/builds/xeus-5.0.0.work，exit 0
- 构建: `cmake --build build-native -j4`，cwd 同上，exit 0（45/45 target，5 个测试可执行体链接成功）
- 运行: `LD_LIBRARY_PATH=<build-native> ctest --output-on-failure`，cwd=build-native，exit 0，5/5 Passed（0.04s/2.68s/0.03s/0.02s/0.03s）
- 首次运行因共享库未在默认加载路径出现符号重定位错误；设置 LD_LIBRARY_PATH 指向构建目录后全部通过（环境类问题，非用例失败）

## 结论

- 上游测试全部枚举、全部实例化、全部实际运行并通过：51/51（100%）。
- 高难度挑战硬门禁要求"实际通过数 == 源码声明总数，失败/跳过/未运行/未实例化/依赖缺失均为 0"，当前满足。
