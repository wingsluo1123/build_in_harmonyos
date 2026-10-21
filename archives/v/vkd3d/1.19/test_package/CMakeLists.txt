cmake_minimum_required(VERSION 3.15)
project(test_vkd3d C)

find_package(vkd3d REQUIRED CONFIG)

add_executable(test_vkd3d test.c)
target_link_libraries(test_vkd3d PRIVATE vkd3d::vkd3d)
