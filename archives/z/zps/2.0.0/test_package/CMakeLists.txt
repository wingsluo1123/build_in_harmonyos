cmake_minimum_required(VERSION 3.15)
project(test_zps C)

# Find the package via Conan-generated CMakeDeps
find_package(zps REQUIRED)

add_executable(test_zps test.c)
target_link_libraries(test_zps zps::zps)

enable_testing()
add_test(NAME test_zps COMMAND test_zps)
