cmake_minimum_required(VERSION 3.15)
project(test_nibbleandahalf C)

# Find the package via Conan-generated CMakeDeps
find_package(nibbleandahalf REQUIRED)

add_executable(test_nibbleandahalf test.c)
target_link_libraries(test_nibbleandahalf nibbleandahalf::nibbleandahalf)

enable_testing()
add_test(NAME test_nibbleandahalf COMMAND test_nibbleandahalf)
