cmake_minimum_required(VERSION 3.15)
project(test_pappl C)

find_package(pappl REQUIRED)
find_package(cups REQUIRED)

add_executable(test_pappl test_pappl.c)
target_link_libraries(test_pappl PRIVATE pappl::pappl cups::cups)
