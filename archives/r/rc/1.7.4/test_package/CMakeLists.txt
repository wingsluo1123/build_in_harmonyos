cmake_minimum_required(VERSION 3.15)
project(test_rc C)

add_executable(test_rc test.c)

enable_testing()
add_test(NAME test_rc COMMAND test_rc)
