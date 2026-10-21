cmake_minimum_required(VERSION 3.15)
project(test_libvdeplug C)

# Find the package via Conan-generated CMakeDeps
find_package(libvdeplug REQUIRED)

add_executable(test_libvdeplug test.c)
target_link_libraries(test_libvdeplug libvdeplug::libvdeplug)

enable_testing()
add_test(NAME test_libvdeplug COMMAND test_libvdeplug)
