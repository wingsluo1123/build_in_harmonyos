cmake_minimum_required(VERSION 3.15)
project(test_bettercap C)

# Find the package via Conan-generated CMakeDeps
find_package(bettercap REQUIRED)

add_executable(test_bettercap test.c)
target_link_libraries(test_bettercap bettercap::bettercap)

enable_testing()
add_test(NAME test_bettercap COMMAND test_bettercap)
