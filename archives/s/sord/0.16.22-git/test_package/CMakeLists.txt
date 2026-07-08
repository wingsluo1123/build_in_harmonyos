cmake_minimum_required(VERSION 3.15)
project(test_sord C)

# Find the package via Conan-generated CMakeDeps
find_package(sord REQUIRED)

add_executable(test_sord test.c)
target_link_libraries(test_sord sord::sord)

enable_testing()
add_test(NAME test_sord COMMAND test_sord)
