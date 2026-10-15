cmake_minimum_required(VERSION 3.15)
project(test_gif C)

# Find the package via Conan-generated CMakeDeps
find_package(gif REQUIRED)

add_executable(test_gif test.c)
target_link_libraries(test_gif gif::gif)

enable_testing()
add_test(NAME test_gif COMMAND test_gif)
