cmake_minimum_required(VERSION 3.15)
project(test_libpaper C)

# Find the package via Conan-generated CMakeDeps
find_package(libpaper REQUIRED)

add_executable(test_libpaper test.c)
target_link_libraries(test_libpaper libpaper::libpaper)

enable_testing()
add_test(NAME test_libpaper COMMAND test_libpaper)
