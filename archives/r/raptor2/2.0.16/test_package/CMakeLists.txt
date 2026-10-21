cmake_minimum_required(VERSION 3.15)
project(test_raptor2 C)

find_package(raptor2 CONFIG REQUIRED)

add_executable(test_raptor2 test_raptor2.c)
target_link_libraries(test_raptor2 PRIVATE raptor2::raptor2)
