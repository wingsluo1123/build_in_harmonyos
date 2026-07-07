cmake_minimum_required(VERSION 3.15)
project(test_blake3 C)

# Find the package via Conan-generated CMakeDeps
find_package(blake3 REQUIRED)

add_executable(test_blake3 test.c)
target_link_libraries(test_blake3 blake3::blake3)

enable_testing()
add_test(NAME test_blake3 COMMAND test_blake3)
