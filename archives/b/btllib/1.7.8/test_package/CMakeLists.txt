cmake_minimum_required(VERSION 3.15)
project(test_btllib C)

# Find the package via Conan-generated CMakeDeps
find_package(btllib REQUIRED)

add_executable(test_btllib test.c)
target_link_libraries(test_btllib btllib::btllib)

enable_testing()
add_test(NAME test_btllib COMMAND test_btllib)
