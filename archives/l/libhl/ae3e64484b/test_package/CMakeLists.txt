cmake_minimum_required(VERSION 3.15)
project(test_libhl C)

# Find the package via Conan-generated CMakeDeps
find_package(libhl REQUIRED)

add_executable(test_libhl test.c)
target_link_libraries(test_libhl libhl::libhl)

enable_testing()
add_test(NAME test_libhl COMMAND test_libhl)
