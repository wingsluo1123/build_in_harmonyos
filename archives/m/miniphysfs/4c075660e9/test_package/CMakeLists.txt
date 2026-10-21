cmake_minimum_required(VERSION 3.15)
project(test_miniphysfs C)

# Find the package via Conan-generated CMakeDeps
find_package(miniphysfs REQUIRED)

add_executable(test_miniphysfs test.c)
target_link_libraries(test_miniphysfs miniphysfs::miniphysfs)

# 端到端消费者用例（rule12）：挂载真实目录→枚举→打开读取→内容校验→清理
add_executable(test_miniphysfs_e2e test_e2e.c)
target_link_libraries(test_miniphysfs_e2e miniphysfs::miniphysfs)

enable_testing()
add_test(NAME test_miniphysfs COMMAND test_miniphysfs)
add_test(NAME test_miniphysfs_e2e COMMAND test_miniphysfs_e2e)
