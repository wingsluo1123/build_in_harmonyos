cmake_minimum_required(VERSION 3.15)
project(test_decker C)

# Find the package via Conan-generated CMakeDeps
find_package(decker REQUIRED)

add_executable(test_decker test.c)
target_link_libraries(test_decker decker::decker)

enable_testing()
add_test(NAME test_decker COMMAND test_decker)
