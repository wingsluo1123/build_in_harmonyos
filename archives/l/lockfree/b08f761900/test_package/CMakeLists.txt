cmake_minimum_required(VERSION 3.15)
project(test_lockfree C)

# Find the package via Conan-generated CMakeDeps
find_package(lockfree REQUIRED)

add_executable(test_lockfree test.c)
target_link_libraries(test_lockfree lockfree::lockfree)

enable_testing()
add_test(NAME test_lockfree COMMAND test_lockfree)
