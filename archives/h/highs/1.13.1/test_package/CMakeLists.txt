cmake_minimum_required(VERSION 3.15)
project(test_highs C)

# Find the package via Conan-generated CMakeDeps
find_package(highs REQUIRED)

add_executable(test_highs test.c)
target_link_libraries(test_highs highs::highs)

enable_testing()
add_test(NAME test_highs COMMAND test_highs)
