cmake_minimum_required(VERSION 3.15)
project(test_libdiscid C)

find_package(libdiscid REQUIRED CONFIG)
add_executable(test_libdiscid test_libdiscid.c)
target_link_libraries(test_libdiscid PRIVATE libdiscid::libdiscid)
