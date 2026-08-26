cmake_minimum_required(VERSION 3.15)
project(whereami_test LANGUAGES C)

find_package(whereami CONFIG REQUIRED)
add_executable(whereami_test test_whereami.c)
target_link_libraries(whereami_test PRIVATE whereami::whereami)
