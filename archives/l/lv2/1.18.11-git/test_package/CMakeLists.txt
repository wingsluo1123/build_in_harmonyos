cmake_minimum_required(VERSION 3.15)
project(test_lv2 C)

# Find the package via Conan-generated CMakeDeps
find_package(lv2 REQUIRED)

add_executable(test_lv2 test.c)
target_link_libraries(test_lv2 lv2::lv2)

enable_testing()
add_test(NAME test_lv2 COMMAND test_lv2)
