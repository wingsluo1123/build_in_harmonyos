cmake_minimum_required(VERSION 3.15)
project(test_liblzw C)

# Find the package via Conan-generated CMakeDeps
find_package(liblzw REQUIRED)

add_executable(test_liblzw test.c)
target_link_libraries(test_liblzw liblzw::liblzw)

enable_testing()
add_test(NAME test_liblzw COMMAND test_liblzw)
