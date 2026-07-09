cmake_minimum_required(VERSION 3.15)
project(test_mise C)

# Find the package via Conan-generated CMakeDeps
find_package(mise REQUIRED)

add_executable(test_mise test.c)
target_link_libraries(test_mise mise::mise)

enable_testing()
add_test(NAME test_mise COMMAND test_mise)
