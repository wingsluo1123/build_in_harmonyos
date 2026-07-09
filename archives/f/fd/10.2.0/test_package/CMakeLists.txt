cmake_minimum_required(VERSION 3.15)
project(test_fd C)

# Find the package via Conan-generated CMakeDeps
find_package(fd REQUIRED)

add_executable(test_fd test.c)
target_link_libraries(test_fd fd::fd)

enable_testing()
add_test(NAME test_fd COMMAND test_fd)
