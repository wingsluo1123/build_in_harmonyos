cmake_minimum_required(VERSION 3.15)
project(test_bear C)

# Find the package via Conan-generated CMakeDeps
find_package(bear REQUIRED)

add_executable(test_bear test.c)
target_link_libraries(test_bear bear::bear)

enable_testing()
add_test(NAME test_bear COMMAND test_bear)
