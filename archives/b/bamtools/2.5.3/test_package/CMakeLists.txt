cmake_minimum_required(VERSION 3.15)
project(test_bamtools C)

# Find the package via Conan-generated CMakeDeps
find_package(bamtools REQUIRED)

add_executable(test_bamtools test.c)
target_link_libraries(test_bamtools bamtools::bamtools)

enable_testing()
add_test(NAME test_bamtools COMMAND test_bamtools)
