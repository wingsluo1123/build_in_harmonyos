cmake_minimum_required(VERSION 3.15)
project(test_bat C)

# Find the package via Conan-generated CMakeDeps
find_package(bat REQUIRED)

add_executable(test_bat test.c)
target_link_libraries(test_bat bat::bat)

enable_testing()
add_test(NAME test_bat COMMAND test_bat)
