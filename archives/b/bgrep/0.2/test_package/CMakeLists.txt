cmake_minimum_required(VERSION 3.15)
project(test_bgrep C)

# Find the package via Conan-generated CMakeDeps
find_package(bgrep REQUIRED)

add_executable(test_bgrep test.c)
target_link_libraries(test_bgrep bgrep::bgrep)

enable_testing()
add_test(NAME test_bgrep COMMAND test_bgrep)
