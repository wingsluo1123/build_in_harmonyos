cmake_minimum_required(VERSION 3.15)
project(test_bubblewrap C)

# Find the package via Conan-generated CMakeDeps
find_package(bubblewrap REQUIRED)

add_executable(test_bubblewrap test.c)
target_link_libraries(test_bubblewrap bubblewrap::bubblewrap)

enable_testing()
add_test(NAME test_bubblewrap COMMAND test_bubblewrap)
