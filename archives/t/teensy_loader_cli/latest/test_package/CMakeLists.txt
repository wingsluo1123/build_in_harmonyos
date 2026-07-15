cmake_minimum_required(VERSION 3.15)
project(test_package C)

add_executable(test_package test_package.c)
enable_testing()
add_test(NAME test_package COMMAND test_package)
