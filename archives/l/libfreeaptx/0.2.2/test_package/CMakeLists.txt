cmake_minimum_required(VERSION 3.15)
project(test_libfreeaptx C)

# Find the package via Conan-generated CMakeDeps
find_package(libfreeaptx REQUIRED)

add_executable(test_libfreeaptx test.c)
target_link_libraries(test_libfreeaptx libfreeaptx::libfreeaptx)

enable_testing()
add_test(NAME test_libfreeaptx COMMAND test_libfreeaptx)
