cmake_minimum_required(VERSION 3.15)
project(test_libexif C)

# Find the package via Conan-generated CMakeDeps
find_package(libexif REQUIRED)

add_executable(test_libexif test.c)
target_link_libraries(test_libexif libexif::libexif)

enable_testing()
add_test(NAME test_libexif COMMAND test_libexif)
