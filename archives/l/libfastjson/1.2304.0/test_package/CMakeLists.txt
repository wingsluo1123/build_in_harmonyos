cmake_minimum_required(VERSION 3.15)
project(test_libfastjson C)

# Find the package via Conan-generated CMakeDeps
find_package(libfastjson REQUIRED)

add_executable(test_libfastjson test.c)
target_link_libraries(test_libfastjson libfastjson::libfastjson)

enable_testing()
add_test(NAME test_libfastjson COMMAND test_libfastjson)
