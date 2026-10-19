cmake_minimum_required(VERSION 3.15)
project(test_nr_micro_shell C)

# Find the package via Conan-generated CMakeDeps
find_package(nr_micro_shell REQUIRED)

add_executable(test_nr_micro_shell test.c)
target_link_libraries(test_nr_micro_shell nr_micro_shell::nr_micro_shell)

enable_testing()
add_test(NAME test_nr_micro_shell COMMAND test_nr_micro_shell)
