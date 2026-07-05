cmake_minimum_required(VERSION 3.15)
project(test_black C)

# Find the package via Conan-generated CMakeDeps
find_package(black REQUIRED)

add_executable(test_black test.c)
target_link_libraries(test_black black::black)

enable_testing()
add_test(NAME test_black COMMAND test_black)
