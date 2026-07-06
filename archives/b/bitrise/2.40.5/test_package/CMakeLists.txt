cmake_minimum_required(VERSION 3.15)
project(test_bitrise C)

# Find the package via Conan-generated CMakeDeps
find_package(bitrise REQUIRED)

add_executable(test_bitrise test.c)
target_link_libraries(test_bitrise bitrise::bitrise)

enable_testing()
add_test(NAME test_bitrise COMMAND test_bitrise)
