cmake_minimum_required(VERSION 3.15)
project(test_source-highlight C)

# Find the package via Conan-generated CMakeDeps
find_package(source-highlight REQUIRED)

add_executable(test_source-highlight test.c)
target_link_libraries(test_source-highlight source-highlight::source-highlight)

enable_testing()
add_test(NAME test_source-highlight COMMAND test_source-highlight)
