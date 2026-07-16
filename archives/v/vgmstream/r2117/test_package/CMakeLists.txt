cmake_minimum_required(VERSION 3.15)
project(test_vgmstream C)

# Find the package via Conan-generated CMakeDeps
find_package(vgmstream REQUIRED)

add_executable(test_vgmstream test.c)
target_link_libraries(test_vgmstream vgmstream::vgmstream)

enable_testing()
add_test(NAME test_vgmstream COMMAND test_vgmstream)
