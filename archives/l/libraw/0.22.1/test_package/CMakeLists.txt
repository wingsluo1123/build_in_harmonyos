cmake_minimum_required(VERSION 3.15)
project(test_libraw C)

# Find the libraw package via Conan-generated CMakeDeps.
# Conan's CMakeDeps creates the target libraw::libraw from cpp_info.libs.
find_package(libraw REQUIRED)

add_executable(test_libraw test.c)
target_link_libraries(test_libraw libraw::libraw)

enable_testing()
add_test(NAME test_libraw COMMAND test_libraw)
