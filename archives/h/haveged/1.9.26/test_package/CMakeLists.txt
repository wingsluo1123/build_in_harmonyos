cmake_minimum_required(VERSION 3.15)
project(test_haveged C)

# Find the package via Conan-generated CMakeDeps
find_package(haveged REQUIRED)

add_executable(test_haveged test.c)
target_link_libraries(test_haveged haveged::haveged)

enable_testing()
add_test(NAME test_haveged COMMAND test_haveged)
