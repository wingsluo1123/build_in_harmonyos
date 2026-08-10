cmake_minimum_required(VERSION 3.15)
project(test_libieee1284 C)

# Find the package via Conan-generated CMakeDeps
find_package(libieee1284 REQUIRED)

add_executable(test_libieee1284 test.c)
target_link_libraries(test_libieee1284 libieee1284::libieee1284)

enable_testing()
add_test(NAME test_libieee1284 COMMAND test_libieee1284)
