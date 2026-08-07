cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(cxxopts REQUIRED)

add_executable(test_package test.cpp)
target_link_libraries(test_package PRIVATE cxxopts::cxxopts)
