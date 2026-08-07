cmake_minimum_required(VERSION 3.15)
project(test_package C)

enable_testing()

find_package(libiodbc REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package libiodbc::libiodbc)

add_test(NAME libiodbc_test COMMAND test_package)
