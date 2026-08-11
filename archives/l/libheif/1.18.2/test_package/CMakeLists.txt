cmake_minimum_required(VERSION 3.15)
project(test_libheif CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libheif REQUIRED)

add_executable(test_libheif test.cpp)
target_link_libraries(test_libheif libheif::heif)

enable_testing()
add_test(NAME test_libheif COMMAND test_libheif)
