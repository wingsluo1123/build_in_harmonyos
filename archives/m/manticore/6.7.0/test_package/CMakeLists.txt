cmake_minimum_required(VERSION 3.15)
project(test_searchd_help C)

# Find the manticore package via Conan-generated CMakeDeps
find_package(manticore REQUIRED)

# Simple test that runs searchd --help via system() call
# This verifies the manticore binary is properly installed and runnable
add_executable(test_searchd_help test_searchd_help.c)
target_link_libraries(test_searchd_help PRIVATE manticore::manticore)

enable_testing()
add_test(NAME test_searchd_help COMMAND test_searchd_help)
