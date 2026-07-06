cmake_minimum_required(VERSION 3.15)
project(test_borgbackup C)

# Find the package via Conan-generated CMakeDeps
find_package(borgbackup REQUIRED)

add_executable(test_borgbackup test.c)
target_link_libraries(test_borgbackup borgbackup::borgbackup)

enable_testing()
add_test(NAME test_borgbackup COMMAND test_borgbackup)
