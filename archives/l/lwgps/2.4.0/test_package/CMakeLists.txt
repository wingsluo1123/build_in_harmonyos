cmake_minimum_required(VERSION 3.15)
project(test_lwgps C)

# Find the package via Conan-generated CMakeDeps
find_package(lwgps REQUIRED)

add_executable(test_lwgps test.c)
target_link_libraries(test_lwgps lwgps::lwgps)

# HarmonyOS 专项测试（任务契约 harmonyos_specific_test）
add_executable(lwgps_ohos_test lwgps_ohos_test.c)
target_link_libraries(lwgps_ohos_test lwgps::lwgps)

enable_testing()
add_test(NAME test_lwgps COMMAND test_lwgps)
add_test(NAME harmonyos_specific_test COMMAND lwgps_ohos_test)