cmake_minimum_required(VERSION 3.15)
project(test_jack C)

# Find the package via Conan-generated CMakeDeps
find_package(jack REQUIRED)

add_executable(test_jack test.c)
target_link_libraries(test_jack jack::jack)

enable_testing()
add_test(NAME test_jack COMMAND test_jack)
