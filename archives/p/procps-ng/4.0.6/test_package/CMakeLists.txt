cmake_minimum_required(VERSION 3.15)
project(test_libproc2 C)

# procps-ng 既是命令行工具包也带 libproc2 库：这里以库消费者身份链接安装
# 包导出的目标（CMakeDeps 生成 procps-ng-config.cmake）。
find_package(procps-ng REQUIRED CONFIG)

add_executable(test_libproc2 src/test_libproc2.c)
target_link_libraries(test_libproc2 PRIVATE procps-ng::procps-ng)

enable_testing()
add_test(NAME test_libproc2 COMMAND test_libproc2)
