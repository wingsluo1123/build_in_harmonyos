cmake_minimum_required(VERSION 3.15)
project(test_freeimage C)

# Find the package via Conan-generated CMakeDeps
find_package(freeimage REQUIRED)

add_executable(test_freeimage test.c)
target_link_libraries(test_freeimage freeimage::freeimage)

enable_testing()
add_test(NAME test_freeimage COMMAND test_freeimage)
