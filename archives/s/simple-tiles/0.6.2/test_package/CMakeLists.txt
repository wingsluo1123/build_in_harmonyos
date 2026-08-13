cmake_minimum_required(VERSION 3.15)
project(simple_tiles_test C)

find_package(simple-tiles REQUIRED)

add_executable(test_simple_tiles test.c)
target_link_libraries(test_simple_tiles PRIVATE simple-tiles::simple-tiles)

enable_testing()
add_test(NAME test_simple_tiles COMMAND test_simple_tiles)
