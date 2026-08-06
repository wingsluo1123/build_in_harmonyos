cmake_minimum_required(VERSION 3.15)
project(test_postgresql C)

# Find the package via Conan-generated CMakeDeps
find_package(postgresql REQUIRED)

add_executable(test_postgresql test.c)
target_link_libraries(test_postgresql postgresql::postgresql)

enable_testing()
add_test(NAME test_postgresql COMMAND test_postgresql)
