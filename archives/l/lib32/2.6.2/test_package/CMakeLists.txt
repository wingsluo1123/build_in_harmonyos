cmake_minimum_required(VERSION 3.15)
project(test_lib32 C)

# Find the package via Conan-generated CMakeDeps
find_package(lib32 REQUIRED)

add_executable(test_lib32 test.c)
target_link_libraries(test_lib32 lib32::lib32)

enable_testing()
add_test(NAME test_lib32 COMMAND test_lib32)
