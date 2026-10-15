cmake_minimum_required(VERSION 3.15)
project(test_par_shapes C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Locate the package through the Conan-generated CMakeDeps files.
find_package(par_shapes REQUIRED)

add_executable(test_par_shapes test_par_shapes.c)
# R1 检视整改：不再手工追加 m——libm 由 package_info() 的 system_libs 声明、
# 经 CMakeDeps 目标传递，此处链接成功即验证该声明生效。
target_link_libraries(test_par_shapes par_shapes::par_shapes)

enable_testing()
add_test(NAME test_par_shapes COMMAND test_par_shapes)
