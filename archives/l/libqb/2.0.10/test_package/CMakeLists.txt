cmake_minimum_required(VERSION 3.15)
project(test_libqb C)

# Find the package via Conan-generated CMakeDeps
find_package(libqb REQUIRED)

add_executable(test_libqb test.c)
target_link_libraries(test_libqb libqb::libqb)

enable_testing()
add_test(NAME test_libqb COMMAND test_libqb)
