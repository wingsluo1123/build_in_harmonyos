cmake_minimum_required(VERSION 3.15)
project(test_picobench CXX)

# 通过 Conan 生成的 CMakeDeps 查找 picobench 包（被测库）
find_package(picobench REQUIRED)
# doctest 2.4.11：上游 test/CMakeLists.txt 经 CPM 拉取 doctest-util 0.1.2 →
# doctest-lib 2.4.11；此处用同版本 Conan 包等价还原（上游测试框架依赖）
find_package(doctest REQUIRED)

# ── 消费者测试（原有）：PICOBENCH 宏注册基准 + runner 真实计时 ──
add_executable(test_picobench test.cpp)
target_link_libraries(test_picobench picobench::picobench)
target_compile_features(test_picobench PRIVATE cxx_std_11)

# ── 上游官方测试镜像 #1：test/basic.cpp（上游原样，6 个 TEST_CASE）──
# 上游：pb_test(basic basic.cpp) → CTest 目标 picobench-basic
# PICOBENCH_DEBUG/PICOBENCH_TEST/PICOBENCH_IMPLEMENT 宏在源文件内自带；
# PICOBENCH_TEST 激活假时钟（picobench.hpp:1519 确定性计时，无真实睡眠），
# 断言含 235 项（report 数值/文本/CSV 三格式全量比对）
add_executable(test_picobench_basic doctest_main.cpp basic.cpp)
target_link_libraries(test_picobench_basic PRIVATE picobench::picobench doctest::doctest)

# ── 上游官方测试镜像 #2：test/multi_cpp/（上游原样，1 个 TEST_CASE，4 TU）──
# 上游：pb_test(multi_cpp main.cpp suite_a.cpp suite_b.cpp suite_b_cont.cpp)
# → CTest 目标 picobench-multi_cpp；验证同套件跨翻译单元的 PICOBENCH 宏注册
# （PICOBENCH_NAMESPACE pb + PICOBENCH_STD_FUNCTION_BENCHMARKS，86 项断言）
add_executable(test_picobench_multi_cpp
    doctest_main.cpp
    multi_cpp/main.cpp
    multi_cpp/suite_a.cpp
    multi_cpp/suite_b.cpp
    multi_cpp/suite_b_cont.cpp)
target_link_libraries(test_picobench_multi_cpp PRIVATE picobench::picobench doctest::doctest)

enable_testing()
add_test(NAME test_picobench COMMAND test_picobench)
add_test(NAME test_picobench_basic COMMAND test_picobench_basic)
add_test(NAME test_picobench_multi_cpp COMMAND test_picobench_multi_cpp)
