cmake_minimum_required(VERSION 3.15)
project(test_libtcd C)

# Find the package via Conan-generated CMakeDeps
find_package(libtcd REQUIRED)

add_executable(test_libtcd test.c)
target_link_libraries(test_libtcd libtcd::libtcd)

enable_testing()
add_test(NAME test_libtcd COMMAND test_libtcd)
