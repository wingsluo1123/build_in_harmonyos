cmake_minimum_required(VERSION 3.15)
project(test_apitrace C)

find_package(apitrace REQUIRED)

add_executable(test_apitrace test.c)

enable_testing()
add_test(NAME test_apitrace COMMAND test_apitrace)
