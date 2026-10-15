cmake_minimum_required(VERSION 3.15)
project(test_libfprint C)

# Find the package via Conan-generated CMakeDeps
find_package(libfprint REQUIRED)

add_executable(test_libfprint test.c)
target_link_libraries(test_libfprint libfprint::libfprint)

enable_testing()
add_test(NAME test_libfprint COMMAND test_libfprint)
