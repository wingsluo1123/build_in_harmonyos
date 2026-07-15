cmake_minimum_required(VERSION 3.15)
project(test_mpg123 C)

# Find the package via Conan-generated CMakeDeps
find_package(mpg123 REQUIRED)

add_executable(test_mpg123 test.c)
target_link_libraries(test_mpg123 mpg123::mpg123)

enable_testing()
add_test(NAME test_mpg123 COMMAND test_mpg123)
