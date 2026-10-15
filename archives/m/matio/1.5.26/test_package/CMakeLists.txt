cmake_minimum_required(VERSION 3.15)
project(test_matio C)

# Find the package via Conan-generated CMakeDeps
find_package(matio REQUIRED)

add_executable(test_matio test.c)
target_link_libraries(test_matio matio::matio)

enable_testing()
add_test(NAME test_matio COMMAND test_matio)
