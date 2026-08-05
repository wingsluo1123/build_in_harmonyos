cmake_minimum_required(VERSION 3.15)
project(test_mini-httpd C)

# Find the package via Conan-generated CMakeDeps
find_package(mini-httpd REQUIRED)

add_executable(test_mini-httpd test.c)
target_link_libraries(test_mini-httpd mini-httpd::mini-httpd)

enable_testing()
add_test(NAME test_mini-httpd COMMAND test_mini-httpd)
