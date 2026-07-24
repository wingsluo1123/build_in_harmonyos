cmake_minimum_required(VERSION 3.15)
project(test_proj C)

# Find the package via Conan-generated CMakeDeps
find_package(proj REQUIRED)

add_executable(test_proj test.c)
target_link_libraries(test_proj proj::proj)

enable_testing()
add_test(NAME test_proj COMMAND test_proj)
