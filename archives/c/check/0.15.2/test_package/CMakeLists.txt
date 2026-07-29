cmake_minimum_required(VERSION 3.15)
project(check_test_package LANGUAGES C)

find_package(Check REQUIRED CONFIG)

add_executable(test_check test_check.c)
target_link_libraries(test_check PRIVATE Check::Check)
