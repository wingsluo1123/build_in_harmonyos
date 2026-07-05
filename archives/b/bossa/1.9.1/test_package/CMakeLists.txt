cmake_minimum_required(VERSION 3.15)
project(test_bossa C)

# Find the package via Conan-generated CMakeDeps
find_package(bossa REQUIRED)

add_executable(test_bossa test.c)
target_link_libraries(test_bossa bossa::bossa)

enable_testing()
add_test(NAME test_bossa COMMAND test_bossa)
