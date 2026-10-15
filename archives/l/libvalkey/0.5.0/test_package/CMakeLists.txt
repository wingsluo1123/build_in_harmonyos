cmake_minimum_required(VERSION 3.15)
project(test_libvalkey C)

# Find the package via Conan-generated CMakeDeps
find_package(libvalkey REQUIRED)

add_executable(test_libvalkey test.c)
target_link_libraries(test_libvalkey libvalkey::libvalkey)

enable_testing()
add_test(NAME test_libvalkey COMMAND test_libvalkey)
