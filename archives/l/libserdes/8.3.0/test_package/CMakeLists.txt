cmake_minimum_required(VERSION 3.15)
project(test_libserdes C)

# Find the package via Conan-generated CMakeDeps
find_package(libserdes REQUIRED)

add_executable(test_libserdes test.c)
target_link_libraries(test_libserdes libserdes::libserdes)

enable_testing()
add_test(NAME test_libserdes COMMAND test_libserdes)
