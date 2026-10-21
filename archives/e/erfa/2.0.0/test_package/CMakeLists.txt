cmake_minimum_required(VERSION 3.15)
project(test_erfa C)

find_package(erfa REQUIRED CONFIG)

add_executable(test_erfa test.c)
target_link_libraries(test_erfa PRIVATE erfa::erfa)

# OHOS 专有适配测试（HarmonyOS PC aarch64/musl/llvm 工具链）
add_executable(test_erfa_ohos test_ohos.c)
target_link_libraries(test_erfa_ohos PRIVATE erfa::erfa)
