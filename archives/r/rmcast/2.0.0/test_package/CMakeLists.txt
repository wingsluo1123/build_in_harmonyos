cmake_minimum_required(VERSION 3.15)
project(rmcast_test LANGUAGES C)

find_package(rmcast CONFIG REQUIRED)
add_executable(rmcast_test test.c)
target_link_libraries(rmcast_test PRIVATE rmcast::rmcast)
