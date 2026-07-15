cmake_minimum_required(VERSION 3.15)
project(test_libpg_query C)

# Find the package via Conan-generated CMakeDeps
find_package(libpg_query REQUIRED)

add_executable(test_libpg_query test.c)
target_link_libraries(test_libpg_query PRIVATE libpg_query::libpg_query)

enable_testing()
add_test(NAME test_libpg_query COMMAND test_libpg_query)
