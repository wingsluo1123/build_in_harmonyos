cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(LibXslt REQUIRED)
find_package(LibXml2 REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package LibXslt::LibXslt LibXml2::LibXml2)

if(NOT CMAKE_CROSSCOMPILING)
    enable_testing()
    add_test(NAME test_package COMMAND test_package)
endif()
