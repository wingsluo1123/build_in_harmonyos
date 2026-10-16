cmake_minimum_required(VERSION 3.15)
project(test_minicsv C)

# Find the package via Conan-generated CMakeDeps
find_package(minicsv REQUIRED)

add_executable(test_minicsv test.c)
target_link_libraries(test_minicsv minicsv::minicsv)

enable_testing()
add_test(NAME test_minicsv COMMAND test_minicsv)