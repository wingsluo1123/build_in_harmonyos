cmake_minimum_required(VERSION 3.15)
project(test_minimap2 C)

# Find the package via Conan-generated CMakeDeps
find_package(minimap2 REQUIRED)

add_executable(test_minimap2 test.c)
target_link_libraries(test_minimap2 minimap2::minimap2)

enable_testing()
add_test(NAME test_minimap2 COMMAND test_minimap2)
