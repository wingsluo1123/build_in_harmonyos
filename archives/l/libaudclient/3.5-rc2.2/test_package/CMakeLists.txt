cmake_minimum_required(VERSION 3.15)
project(test_libaudclient C)

find_package(libaudclient REQUIRED CONFIG)

add_executable(test_libaudclient test.c)
target_link_libraries(test_libaudclient PRIVATE libaudclient::libaudclient)
