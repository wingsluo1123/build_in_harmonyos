cmake_minimum_required(VERSION 3.15)
project(test_fmt CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fmt REQUIRED)

add_executable(test_fmt test.cpp)
target_link_libraries(test_fmt fmt::fmt)

enable_testing()
add_test(NAME test_fmt COMMAND test_fmt)
