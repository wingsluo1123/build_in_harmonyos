cmake_minimum_required(VERSION 3.15)
project(test_xsimd C)

# Find the package via Conan-generated CMakeDeps
find_package(xsimd REQUIRED)

add_executable(test_xsimd test.c)
target_link_libraries(test_xsimd xsimd::xsimd)

enable_testing()
add_test(NAME test_xsimd COMMAND test_xsimd)
