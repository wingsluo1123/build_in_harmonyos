cmake_minimum_required(VERSION 3.15)
project(test_bpm-tools C)

# Find the package via Conan-generated CMakeDeps
find_package(bpm-tools REQUIRED)

add_executable(test_bpm-tools test.c)
target_link_libraries(test_bpm-tools bpm-tools::bpm-tools)

enable_testing()
add_test(NAME test_bpm-tools COMMAND test_bpm-tools)
