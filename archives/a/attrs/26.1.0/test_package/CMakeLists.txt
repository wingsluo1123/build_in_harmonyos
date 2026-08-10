cmake_minimum_required(VERSION 3.15)
project(test_attrs C)

# Find the package via Conan-generated CMakeDeps
find_package(attrs REQUIRED)

add_executable(test_attrs test.c)
target_link_libraries(test_attrs attrs::attrs)

enable_testing()
add_test(NAME test_attrs COMMAND test_attrs)
