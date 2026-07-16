cmake_minimum_required(VERSION 3.15)
project(test_texi2html C)

add_executable(test_texi2html test.c)
enable_testing()
add_test(NAME test_texi2html COMMAND test_texi2html)
