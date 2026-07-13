cmake_minimum_required(VERSION 3.15)
project(test_ittapi C)

# Find the package via Conan-generated CMakeDeps
find_package(ittapi REQUIRED)

add_executable(test_ittapi test.c)
target_link_libraries(test_ittapi ittapi::ittapi)

enable_testing()
add_test(NAME test_ittapi COMMAND test_ittapi)
