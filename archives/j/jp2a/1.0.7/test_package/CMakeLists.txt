cmake_minimum_required(VERSION 3.15)
project(test_jp2a C)

# Find the package via Conan-generated CMakeDeps
find_package(jp2a REQUIRED)

add_executable(test_jp2a test.c)
target_link_libraries(test_jp2a jp2a::jp2a)

enable_testing()
add_test(NAME test_jp2a COMMAND test_jp2a)
