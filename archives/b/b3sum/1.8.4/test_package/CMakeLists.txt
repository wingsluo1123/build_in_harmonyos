cmake_minimum_required(VERSION 3.15)
project(test_b3sum C)

# Find the package via Conan-generated CMakeDeps
find_package(b3sum REQUIRED)

add_executable(test_b3sum test.c)
target_link_libraries(test_b3sum b3sum::b3sum)

enable_testing()
add_test(NAME test_b3sum COMMAND test_b3sum)
