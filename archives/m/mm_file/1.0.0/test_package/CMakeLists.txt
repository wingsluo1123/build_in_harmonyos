cmake_minimum_required(VERSION 3.15)
project(test_mm_file CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(mm_file REQUIRED CONFIG)

add_executable(test_mm_file test.cpp)
target_link_libraries(test_mm_file mm_file::mm_file)

enable_testing()
add_test(NAME test_mm_file COMMAND test_mm_file)
