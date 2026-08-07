cmake_minimum_required(VERSION 3.15)
project(test_pound C)

# Find the package via Conan-generated CMakeDeps
find_package(pound REQUIRED)

add_executable(test_pound test.c)
target_link_libraries(test_pound pound::pound)

enable_testing()
add_test(NAME test_pound COMMAND test_pound)
