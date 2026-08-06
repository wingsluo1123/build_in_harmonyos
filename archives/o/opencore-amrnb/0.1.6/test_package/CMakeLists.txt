cmake_minimum_required(VERSION 3.15)
project(test_package C)

add_executable(test_package test_amrnb.c)
find_package(opencore-amrnb CONFIG REQUIRED)
target_link_libraries(test_package PRIVATE opencore-amrnb::opencore-amrnb)
