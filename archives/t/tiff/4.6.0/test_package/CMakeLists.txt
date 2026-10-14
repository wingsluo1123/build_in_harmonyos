cmake_minimum_required(VERSION 3.15)
project(test_tiff C)

# Find the package via Conan-generated CMakeDeps
find_package(tiff REQUIRED CONFIG)

add_executable(test_tiff test_tiff.c)
target_link_libraries(test_tiff PRIVATE tiff::tiff)

enable_testing()
add_test(NAME test_tiff COMMAND test_tiff)