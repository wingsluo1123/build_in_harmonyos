cmake_minimum_required(VERSION 3.15)
project(test_popt C)

# Find the package via Conan-generated CMakeDeps
find_package(popt REQUIRED)

add_executable(test_popt test.c)
target_link_libraries(test_popt popt::popt)

enable_testing()
add_test(NAME test_popt COMMAND test_popt)
