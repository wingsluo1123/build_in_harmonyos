cmake_minimum_required(VERSION 3.15)
project(wv_test C)

find_package(wv REQUIRED CONFIG)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE wv::wv)
