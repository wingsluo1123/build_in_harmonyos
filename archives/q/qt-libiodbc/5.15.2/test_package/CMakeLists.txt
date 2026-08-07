cmake_minimum_required(VERSION 3.15)
project(test_package C)

enable_testing()

add_executable(test_package test_package.c)
add_test(NAME qt_libiodbc_test COMMAND test_package)
