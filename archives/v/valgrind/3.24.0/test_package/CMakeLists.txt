cmake_minimum_required(VERSION 3.15)
project(test_valgrind C)

# Find the package via Conan-generated CMakeDeps
find_package(valgrind REQUIRED)

add_executable(test_valgrind test.c)
target_link_libraries(test_valgrind valgrind::valgrind)

enable_testing()
add_test(NAME test_valgrind COMMAND test_valgrind)
