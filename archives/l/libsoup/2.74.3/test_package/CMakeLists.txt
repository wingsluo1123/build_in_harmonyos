cmake_minimum_required(VERSION 3.15)
project(test_libsoup C)

# Find libsoup via Conan-generated CMakeDeps
find_package(libsoup REQUIRED)

add_executable(test_libsoup test.c)
target_link_libraries(test_libsoup libsoup::libsoup)

enable_testing()
add_test(NAME test_libsoup COMMAND test_libsoup)
