cmake_minimum_required(VERSION 3.15)
project(test_nsnake C)

# Find the package via Conan-generated CMakeDeps
find_package(nsnake REQUIRED)

add_executable(test_nsnake test.c)
target_link_libraries(test_nsnake nsnake::nsnake)

enable_testing()
add_test(NAME test_nsnake COMMAND test_nsnake)
