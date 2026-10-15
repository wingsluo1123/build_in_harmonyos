cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(sox_ng REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE sox_ng::sox_ng m)

include(CTest)
add_test(NAME sox_ng_consumer COMMAND test_package)
