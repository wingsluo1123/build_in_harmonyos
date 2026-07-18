cmake_minimum_required(VERSION 3.15)
project(test_gnu-typist C)

# Find the package via Conan-generated CMakeDeps
find_package(gnu-typist REQUIRED)

add_executable(test_gnu-typist test.c)
# For application packages, link against the installed package
target_link_libraries(test_gnu-typist gnu-typist::gnu-typist)

enable_testing()
add_test(NAME test_gnu-typist COMMAND test_gnu-typist)