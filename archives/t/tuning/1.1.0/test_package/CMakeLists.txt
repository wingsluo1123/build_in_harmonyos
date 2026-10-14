cmake_minimum_required(VERSION 3.15)
project(test_tuning CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = tuning)
find_package(tuning REQUIRED)

# 消费者测试：真实调用 Tunings 公共 API（SCL/KBM 解析、频率映射、错误路径）
add_executable(test_tuning test_tuning.cpp)
target_link_libraries(test_tuning PRIVATE tuning::tuning)

# 鸿蒙特有测试：OHOS aarch64 平台 + OHOS libc/文件系统/locale 集成
add_executable(test_tuning_harmonyos test_tuning_harmonyos.cpp)
target_link_libraries(test_tuning_harmonyos PRIVATE tuning::tuning)

enable_testing()
add_test(NAME test_tuning COMMAND test_tuning)
add_test(NAME test_tuning_harmonyos COMMAND test_tuning_harmonyos)
