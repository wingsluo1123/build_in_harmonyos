cmake_minimum_required(VERSION 3.15)
project(test_fwupd C)

# Find the package via Conan-generated CMakeDeps
find_package(fwupd REQUIRED)

add_executable(test_fwupd test.c)
target_link_libraries(test_fwupd fwupd::fwupd)

enable_testing()
add_test(NAME test_fwupd COMMAND test_fwupd)
