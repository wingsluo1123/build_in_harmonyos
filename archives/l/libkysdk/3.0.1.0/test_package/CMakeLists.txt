cmake_minimum_required(VERSION 3.15)
project(test_libkysdk C)

# Find the package via Conan-generated CMakeDeps
find_package(libkysdk REQUIRED)

add_executable(test_libkysdk test_kysdk.c)
target_link_libraries(test_libkysdk libkysdk::libkysdk)

enable_testing()
add_test(NAME test_libkysdk COMMAND test_libkysdk)
