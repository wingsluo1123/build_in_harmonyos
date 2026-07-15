cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(spirv-headers CONFIG REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package spirv-headers::spirv-headers)
