cmake_minimum_required(VERSION 3.15)
project(test_libvldmail C)

# Find the package via Conan-generated CMakeDeps
find_package(libvldmail REQUIRED)

add_executable(test_libvldmail test.c)
target_link_libraries(test_libvldmail libvldmail::libvldmail)

enable_testing()
add_test(NAME test_libvldmail COMMAND test_libvldmail)
