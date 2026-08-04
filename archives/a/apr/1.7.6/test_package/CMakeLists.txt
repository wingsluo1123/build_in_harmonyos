cmake_minimum_required(VERSION 3.15)
project(test_apr C)

# Find the package via Conan-generated CMakeDeps
find_package(APR REQUIRED)

add_executable(test_apr test.c)
target_link_libraries(test_apr APR::APR)

enable_testing()
add_test(NAME test_apr COMMAND test_apr)
