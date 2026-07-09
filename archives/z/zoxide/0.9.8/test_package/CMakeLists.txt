cmake_minimum_required(VERSION 3.15)
project(test_zoxide C)

# Find the package via Conan-generated CMakeDeps
find_package(zoxide REQUIRED)

add_executable(test_zoxide test.c)
target_link_libraries(test_zoxide zoxide::zoxide)

enable_testing()
add_test(NAME test_zoxide COMMAND test_zoxide)
