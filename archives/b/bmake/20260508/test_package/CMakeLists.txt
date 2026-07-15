cmake_minimum_required(VERSION 3.15)
project(test_bmake C)

# Find the package via Conan-generated CMakeDeps
find_package(bmake REQUIRED)

add_executable(test_bmake test.c)
target_link_libraries(test_bmake bmake::bmake)

enable_testing()
add_test(NAME test_bmake COMMAND test_bmake)
