cmake_minimum_required(VERSION 3.15)
project(test_blend2d C)

# Find the package via Conan-generated CMakeDeps
find_package(blend2d REQUIRED)

add_executable(test_blend2d test.c)
target_link_libraries(test_blend2d blend2d::blend2d)

enable_testing()
add_test(NAME test_blend2d COMMAND test_blend2d)
