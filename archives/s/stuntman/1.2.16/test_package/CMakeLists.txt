cmake_minimum_required(VERSION 3.15)
project(test_stuntman C)

add_executable(test_stuntman test.c)

enable_testing()
add_test(NAME test_stuntman COMMAND test_stuntman)
