cmake_minimum_required(VERSION 3.15)
project(test_zeromq C)

# Find the package via Conan-generated CMakeDeps
find_package(zeromq REQUIRED)

add_executable(test_zeromq test.c)
target_link_libraries(test_zeromq zeromq::zeromq)

enable_testing()
add_test(NAME test_zeromq COMMAND test_zeromq)
