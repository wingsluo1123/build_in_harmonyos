cmake_minimum_required(VERSION 3.15)
project(test_easytag C)

# Find the package via Conan-generated CMakeDeps
find_package(easytag REQUIRED)

add_executable(test_easytag test.c)
target_link_libraries(test_easytag easytag::easytag)

enable_testing()
add_test(NAME test_easytag COMMAND test_easytag)
