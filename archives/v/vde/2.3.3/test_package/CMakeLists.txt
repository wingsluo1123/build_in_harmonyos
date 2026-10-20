cmake_minimum_required(VERSION 3.15)
project(test_vde C)

find_package(vde REQUIRED CONFIG)

add_executable(test_vde test_vde.c)
target_link_libraries(test_vde PRIVATE vde::vde)
