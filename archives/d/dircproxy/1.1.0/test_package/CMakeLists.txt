cmake_minimum_required(VERSION 3.15)
project(test_dircproxy C)

# Find the package via Conan-generated CMakeDeps
find_package(dircproxy REQUIRED)

add_executable(test_dircproxy test.c)
target_link_libraries(test_dircproxy dircproxy::dircproxy)

enable_testing()
add_test(NAME test_dircproxy COMMAND test_dircproxy)
