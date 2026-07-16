cmake_minimum_required(VERSION 3.15)
project(test_flake C)

# Find the package via Conan-generated CMakeDeps
find_package(flake REQUIRED)

add_executable(test_flake test.c)
target_link_libraries(test_flake flake::flake)

enable_testing()
add_test(NAME test_flake COMMAND test_flake)
