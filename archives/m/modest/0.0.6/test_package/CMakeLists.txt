cmake_minimum_required(VERSION 3.15)
project(test_modest C)

# Find the package via Conan-generated CMakeDeps
find_package(modest REQUIRED)

add_executable(test_modest test.c)
target_link_libraries(test_modest modest::modest)

enable_testing()
add_test(NAME test_modest COMMAND test_modest)
