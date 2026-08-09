cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libbsd REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package libbsd::libbsd)
