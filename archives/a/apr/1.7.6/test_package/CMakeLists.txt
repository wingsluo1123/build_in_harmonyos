cmake_minimum_required(VERSION 3.8)
project(test_package C)

find_package(apr REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package apr::apr-1)
