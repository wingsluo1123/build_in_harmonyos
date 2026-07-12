cmake_minimum_required(VERSION 3.15)
project(test_cmatrix C)

add_executable(test_cmatrix test.c)
target_link_libraries(test_cmatrix PRIVATE)

enable_testing()
add_test(NAME test_cmatrix COMMAND test_cmatrix)