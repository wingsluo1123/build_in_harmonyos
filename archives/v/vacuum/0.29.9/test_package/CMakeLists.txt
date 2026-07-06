cmake_minimum_required(VERSION 3.15)
project(test_vacuum C)

# Find the package via Conan-generated CMakeDeps
find_package(vacuum REQUIRED)

add_executable(test_vacuum test.c)
target_link_libraries(test_vacuum vacuum::vacuum)

enable_testing()
add_test(NAME test_vacuum COMMAND test_vacuum)
