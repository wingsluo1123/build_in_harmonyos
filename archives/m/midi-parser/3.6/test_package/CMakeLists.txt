cmake_minimum_required(VERSION 3.15)
project(test_midi-parser C)

# Find the package via Conan-generated CMakeDeps
find_package(midi-parser REQUIRED)

add_executable(test_midi-parser test.c)
target_link_libraries(test_midi-parser midi-parser::midi-parser)

enable_testing()
add_test(NAME test_midi-parser COMMAND test_midi-parser)
