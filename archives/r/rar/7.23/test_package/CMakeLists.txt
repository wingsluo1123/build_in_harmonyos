cmake_minimum_required(VERSION 3.15)
project(test_rar CXX)

find_package(rar REQUIRED CONFIG)

add_executable(test_rar test.cpp)
target_link_libraries(test_rar PRIVATE rar::rar)
