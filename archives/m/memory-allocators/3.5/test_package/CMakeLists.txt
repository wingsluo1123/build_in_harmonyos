cmake_minimum_required(VERSION 3.15)
project(test_memory-allocators CXX)

# Find the package via Conan-generated CMakeDeps
find_package(memory-allocators REQUIRED)

add_executable(test_memory-allocators test.cpp)
target_link_libraries(test_memory-allocators memory-allocators::memory-allocators)

enable_testing()
add_test(NAME test_memory-allocators COMMAND test_memory-allocators)