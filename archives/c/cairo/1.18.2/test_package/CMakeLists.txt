cmake_minimum_required(VERSION 3.15)
project(test_cairo C)

# Find the package via Conan-generated CMakeDeps
find_package(cairo REQUIRED)

add_executable(test_cairo test.c)
target_link_libraries(test_cairo cairo::cairo)

enable_testing()
add_test(NAME test_cairo COMMAND test_cairo)
