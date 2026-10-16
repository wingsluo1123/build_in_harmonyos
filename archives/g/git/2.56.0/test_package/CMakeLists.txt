cmake_minimum_required(VERSION 3.15)
project(test_git C)

# Find the package via Conan-generated CMakeDeps
find_package(git REQUIRED)

add_executable(test_git test.c)
target_link_libraries(test_git git::git)

enable_testing()
add_test(NAME test_git COMMAND test_git)
