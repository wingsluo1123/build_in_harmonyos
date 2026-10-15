cmake_minimum_required(VERSION 3.16)
project(cpp_async_harmonyos_test LANGUAGES CXX)

# HarmonyOS 专项测试 — cpp-async 1.2.0 完整消费者端到端用例（赛事规则 12）
# 可复现构建入口:
#   cmake -S . -B build -DCMAKE_PREFIX_PATH=<conan cpp-async 包 prefix>
#   cmake --build build
# 亦可直接编译（无 CMake 依赖）:
#   clang++ -std=c++20 -I<src include> -pthread harmonyos_consumer_e2e_test.cpp

find_package(cpp-async REQUIRED)

add_executable(harmonyos_consumer_e2e_test harmonyos_consumer_e2e_test.cpp)
target_link_libraries(harmonyos_consumer_e2e_test PRIVATE cpp-async::cpp-async)
target_compile_features(harmonyos_consumer_e2e_test PRIVATE cxx_std_20)

enable_testing()
add_test(NAME harmonyos_consumer_e2e_test COMMAND harmonyos_consumer_e2e_test)