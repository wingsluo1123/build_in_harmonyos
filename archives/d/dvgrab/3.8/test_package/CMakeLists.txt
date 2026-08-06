cmake_minimum_required(VERSION 3.15)
project(test_dvgrab C)

# Find the package via Conan-generated CMakeDeps
find_package(dvgrab REQUIRED)

# Simple test executable — dvgrab is a command-line tool,
# so the actual test runs the dvgrab binary in test()
add_executable(test_dvgrab test_dvgrab.c)
target_link_libraries(test_dvgrab dvgrab::dvgrab)

enable_testing()
add_test(NAME test_dvgrab COMMAND test_dvgrab)
