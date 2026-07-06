cmake_minimum_required(VERSION 3.15)
project(test_basedpyright C)

# Find the package via Conan-generated CMakeDeps
find_package(basedpyright REQUIRED)

add_executable(test_basedpyright test.c)
target_link_libraries(test_basedpyright basedpyright::basedpyright)

enable_testing()
add_test(NAME test_basedpyright COMMAND test_basedpyright)
