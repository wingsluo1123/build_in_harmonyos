cmake_minimum_required(VERSION 3.15)
project(test_brotli C)

# Find the package via Conan-generated CMakeDeps
find_package(brotli REQUIRED)

add_executable(test_brotli test.c)
target_link_libraries(test_brotli brotli::brotli)

enable_testing()
add_test(NAME test_brotli COMMAND test_brotli)
