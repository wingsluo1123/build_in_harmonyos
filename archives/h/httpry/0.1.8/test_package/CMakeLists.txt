cmake_minimum_required(VERSION 3.15)
project(test_httpry C)

# Find the package via Conan-generated CMakeDeps
find_package(httpry REQUIRED)

add_executable(test_httpry test.c)
target_link_libraries(test_httpry httpry::httpry)

enable_testing()
add_test(NAME test_httpry COMMAND test_httpry)
