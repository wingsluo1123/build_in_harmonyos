cmake_minimum_required(VERSION 3.15)
project(test_botan C)

# Find the package via Conan-generated CMakeDeps
find_package(botan REQUIRED)

add_executable(test_botan test.c)
target_link_libraries(test_botan botan::botan)

enable_testing()
add_test(NAME test_botan COMMAND test_botan)
