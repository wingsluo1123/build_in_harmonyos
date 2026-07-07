cmake_minimum_required(VERSION 3.15)
project(test_bottom C)

# Find the package via Conan-generated CMakeDeps
find_package(bottom REQUIRED)

add_executable(test_bottom test.c)
target_link_libraries(test_bottom bottom::bottom)

enable_testing()
add_test(NAME test_bottom COMMAND test_bottom)
