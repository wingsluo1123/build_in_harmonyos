cmake_minimum_required(VERSION 3.15)
project(test_a2ps C)

# Find the package via Conan-generated CMakeDeps
find_package(a2ps REQUIRED)

add_executable(test_a2ps test.c)
target_link_libraries(test_a2ps a2ps::a2ps)

enable_testing()
add_test(NAME test_a2ps COMMAND test_a2ps)
