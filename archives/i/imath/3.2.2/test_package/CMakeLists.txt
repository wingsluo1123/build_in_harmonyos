cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Imath REQUIRED)

add_executable(test_package src/test.cpp)
target_link_libraries(test_package Imath::Imath)

enable_testing()
add_test(NAME test_package COMMAND test_package)
