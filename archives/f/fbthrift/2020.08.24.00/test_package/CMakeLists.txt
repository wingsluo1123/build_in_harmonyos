cmake_minimum_required(VERSION 3.15)
project(test_fbthrift C)

# Find the package via Conan-generated CMakeDeps
find_package(fbthrift REQUIRED)

add_executable(test_fbthrift test.c)
target_link_libraries(test_fbthrift fbthrift::fbthrift)

enable_testing()
add_test(NAME test_fbthrift COMMAND test_fbthrift)
