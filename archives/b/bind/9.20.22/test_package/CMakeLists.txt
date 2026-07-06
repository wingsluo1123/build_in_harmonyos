cmake_minimum_required(VERSION 3.15)
project(test_bind C)

# Find the package via Conan-generated CMakeDeps
find_package(bind REQUIRED)

add_executable(test_bind test.c)
target_link_libraries(test_bind bind::bind)

enable_testing()
add_test(NAME test_bind COMMAND test_bind)
