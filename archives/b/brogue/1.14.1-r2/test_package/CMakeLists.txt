cmake_minimum_required(VERSION 3.15)
project(test_brogue C)

# Find the package via Conan-generated CMakeDeps
find_package(brogue REQUIRED)

add_executable(test_brogue test.c)
target_link_libraries(test_brogue brogue::brogue)

enable_testing()
add_test(NAME test_brogue COMMAND test_brogue)
