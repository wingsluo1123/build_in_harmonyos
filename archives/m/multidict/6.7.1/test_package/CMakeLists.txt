cmake_minimum_required(VERSION 3.15)
project(test_multidict C)

# Find the package via Conan-generated CMakeDeps
find_package(multidict REQUIRED)

add_executable(test_multidict test.c)
target_link_libraries(test_multidict multidict::multidict)

enable_testing()
add_test(NAME test_multidict COMMAND test_multidict)
