cmake_minimum_required(VERSION 3.15)
project(test_bison C)

# Find the package via Conan-generated CMakeDeps
find_package(bison REQUIRED)

add_executable(test_bison test.c)
target_link_libraries(test_bison bison::bison)

enable_testing()
add_test(NAME test_bison COMMAND test_bison)
