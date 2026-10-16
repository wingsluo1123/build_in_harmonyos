cmake_minimum_required(VERSION 3.15)
project(test_mjs C)

find_package(mjs REQUIRED CONFIG)

add_executable(test_mjs test_mjs.c)
target_link_libraries(test_mjs PRIVATE mjs::mjs)
