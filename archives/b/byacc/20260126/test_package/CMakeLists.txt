cmake_minimum_required(VERSION 3.15)
project(test_byacc C)

# Find the package via Conan-generated CMakeDeps
find_package(byacc REQUIRED)

add_executable(test_byacc test.c)
target_link_libraries(test_byacc byacc::byacc)

enable_testing()
add_test(NAME test_byacc COMMAND test_byacc)
