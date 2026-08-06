cmake_minimum_required(VERSION 3.15)
project(test_mold C)

add_executable(test_mold test.c)

enable_testing()
add_test(NAME test_mold COMMAND test_mold)
