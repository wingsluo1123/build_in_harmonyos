cmake_minimum_required(VERSION 3.15)
project(test_ctags C)

# Simple test that just compiles and runs
add_executable(test_ctags test.c)

enable_testing()
add_test(NAME test_ctags COMMAND test_ctags)
