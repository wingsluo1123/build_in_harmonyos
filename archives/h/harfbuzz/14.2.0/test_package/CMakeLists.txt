cmake_minimum_required(VERSION 3.15)
project(test_harfbuzz C)

find_package(harfbuzz REQUIRED)

add_executable(test_harfbuzz test.c)
target_link_libraries(test_harfbuzz harfbuzz::harfbuzz)