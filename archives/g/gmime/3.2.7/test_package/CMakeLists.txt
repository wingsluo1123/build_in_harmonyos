cmake_minimum_required(VERSION 3.15)
project(test_gmime C)

find_package(gmime REQUIRED)

add_executable(test_gmime test_gmime.c)
target_link_libraries(test_gmime gmime::gmime)
