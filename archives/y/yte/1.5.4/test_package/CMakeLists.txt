cmake_minimum_required(VERSION 3.15)
project(test_yte C)

# Find the package via Conan-generated CMakeDeps
find_package(yte REQUIRED)

add_executable(test_yte test.c)
target_link_libraries(test_yte yte::yte)

enable_testing()
add_test(NAME test_yte COMMAND test_yte)
