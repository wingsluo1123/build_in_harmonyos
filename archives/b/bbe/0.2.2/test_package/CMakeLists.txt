cmake_minimum_required(VERSION 3.15)
project(test_bbe C)

# Find the package via Conan-generated CMakeDeps
find_package(bbe REQUIRED)

add_executable(test_bbe test.c)
target_link_libraries(test_bbe bbe::bbe)

enable_testing()
add_test(NAME test_bbe COMMAND test_bbe)
