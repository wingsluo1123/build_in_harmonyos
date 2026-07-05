cmake_minimum_required(VERSION 3.15)
project(test_boxes C)

# Find the package via Conan-generated CMakeDeps
find_package(boxes REQUIRED)

add_executable(test_boxes test.c)
target_link_libraries(test_boxes boxes::boxes)

enable_testing()
add_test(NAME test_boxes COMMAND test_boxes)
