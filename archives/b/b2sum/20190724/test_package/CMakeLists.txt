cmake_minimum_required(VERSION 3.15)
project(test_b2sum C)

# Find the package via Conan-generated CMakeDeps
find_package(b2sum REQUIRED)

add_executable(test_b2sum test.c)
target_link_libraries(test_b2sum b2sum::b2sum)

enable_testing()
add_test(NAME test_b2sum COMMAND test_b2sum)
