cmake_minimum_required(VERSION 3.15)
project(test_bzip2 C)

# Find the package via Conan-generated CMakeDeps
find_package(bzip2 REQUIRED)

add_executable(test_bzip2 test.c)
target_link_libraries(test_bzip2 bzip2::bzip2)

enable_testing()
add_test(NAME test_bzip2 COMMAND test_bzip2)
