cmake_minimum_required(VERSION 3.15)
project(test_symlinks C)

enable_testing()
add_executable(test_symlinks test.c)
add_test(NAME test_symlinks COMMAND test_symlinks)
