cmake_minimum_required(VERSION 3.15)
project(test_traceroute C)

# Find the package via Conan-generated CMakeDeps
find_package(traceroute REQUIRED)

add_executable(test_traceroute test.c)
target_link_libraries(test_traceroute traceroute::traceroute)

enable_testing()
add_test(NAME test_traceroute COMMAND test_traceroute)
