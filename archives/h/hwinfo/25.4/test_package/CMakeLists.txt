cmake_minimum_required(VERSION 3.15)
project(test_hwinfo C)

find_package(hwinfo REQUIRED)

add_executable(test_hwinfo test_hwinfo.c)
target_link_libraries(test_hwinfo PRIVATE hwinfo::hwinfo)
