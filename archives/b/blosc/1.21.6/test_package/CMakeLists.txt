cmake_minimum_required(VERSION 3.15)
project(test_blosc C)

# Find the package via Conan-generated CMakeDeps
find_package(blosc REQUIRED)

add_executable(test_blosc test.c)
target_link_libraries(test_blosc blosc::blosc)

enable_testing()
add_test(NAME test_blosc COMMAND test_blosc)
