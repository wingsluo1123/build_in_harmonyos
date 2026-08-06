cmake_minimum_required(VERSION 3.15)
project(test_isync C)

add_executable(test_isync test_isync.c)

enable_testing()
add_test(NAME test_isync COMMAND test_isync)
