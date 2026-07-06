cmake_minimum_required(VERSION 3.15)
project(test_bc C)

# Find the package via Conan-generated CMakeDeps
find_package(bc REQUIRED)

add_executable(test_bc test.c)
target_link_libraries(test_bc bc::bc)

enable_testing()
add_test(NAME test_bc COMMAND test_bc)
