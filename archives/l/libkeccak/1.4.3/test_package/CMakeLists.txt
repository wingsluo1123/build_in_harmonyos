cmake_minimum_required(VERSION 3.15)
project(test_libkeccak C)

# Find the package via Conan-generated CMakeDeps
find_package(libkeccak REQUIRED)

add_executable(test_libkeccak test.c)
target_link_libraries(test_libkeccak libkeccak::libkeccak)

enable_testing()
add_test(NAME test_libkeccak COMMAND test_libkeccak)
