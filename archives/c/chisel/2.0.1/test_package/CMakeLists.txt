cmake_minimum_required(VERSION 3.15)
project(test_chisel C)

# Find the package via Conan-generated CMakeDeps
find_package(chisel REQUIRED)

add_executable(test_chisel test.c)
target_link_libraries(test_chisel chisel::chisel)

enable_testing()
add_test(NAME test_chisel COMMAND test_chisel)
