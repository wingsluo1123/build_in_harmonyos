cmake_minimum_required(VERSION 3.15)
project(test_binwalk C)

# Find the package via Conan-generated CMakeDeps
find_package(binwalk REQUIRED)

add_executable(test_binwalk test.c)
target_link_libraries(test_binwalk binwalk::binwalk)

enable_testing()
add_test(NAME test_binwalk COMMAND test_binwalk)
