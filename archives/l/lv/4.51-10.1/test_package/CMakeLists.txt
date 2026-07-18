cmake_minimum_required(VERSION 3.15)
project(test_lv C)

# Find the package via Conan-generated CMakeDeps
find_package(lv REQUIRED)

add_executable(test_lv test.c)
target_link_libraries(test_lv lv::lv)

enable_testing()
add_test(NAME test_lv COMMAND test_lv)
