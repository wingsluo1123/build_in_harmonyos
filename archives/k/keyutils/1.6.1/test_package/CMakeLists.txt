cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(keyutils REQUIRED)

add_executable(test_package main.c)
target_link_libraries(test_package keyutils::keyutils)
