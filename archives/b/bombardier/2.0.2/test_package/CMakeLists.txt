cmake_minimum_required(VERSION 3.15)
project(test_bombardier C)

# Find the package via Conan-generated CMakeDeps
find_package(bombardier REQUIRED)

add_executable(test_bombardier test.c)
target_link_libraries(test_bombardier bombardier::bombardier)

enable_testing()
add_test(NAME test_bombardier COMMAND test_bombardier)
