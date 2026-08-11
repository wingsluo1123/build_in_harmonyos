cmake_minimum_required(VERSION 3.15)
project(test_ffms2 C)

# Find the package via Conan-generated CMakeDeps
find_package(ffms2 REQUIRED)

add_executable(test_ffms2 test.c)
target_link_libraries(test_ffms2 ffms2::ffms2)

enable_testing()
add_test(NAME test_ffms2 COMMAND test_ffms2)
