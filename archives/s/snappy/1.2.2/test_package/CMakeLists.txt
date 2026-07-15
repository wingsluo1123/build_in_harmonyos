cmake_minimum_required(VERSION 3.15)
project(test_snappy CXX)

# Find the package via Conan-generated CMakeDeps
find_package(snappy REQUIRED)

add_executable(test_snappy test.cpp)
target_link_libraries(test_snappy snappy::snappy)

enable_testing()
add_test(NAME test_snappy COMMAND test_snappy)
