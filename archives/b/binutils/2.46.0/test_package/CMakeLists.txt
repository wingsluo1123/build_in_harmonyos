cmake_minimum_required(VERSION 3.15)
project(test_binutils C)

# Find the package via Conan-generated CMakeDeps
find_package(binutils REQUIRED)

add_executable(test_binutils test.c)
target_link_libraries(test_binutils binutils::binutils)

enable_testing()
add_test(NAME test_binutils COMMAND test_binutils)
