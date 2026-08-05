cmake_minimum_required(VERSION 3.15)
project(test_agg C)

# Find the package via Conan-generated CMakeDeps
find_package(agg REQUIRED)

add_executable(test_agg test.c)
target_link_libraries(test_agg agg::agg)

enable_testing()
add_test(NAME test_agg COMMAND test_agg)
