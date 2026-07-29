cmake_minimum_required(VERSION 3.15)
project(ncurses_test_package LANGUAGES C)

find_package(ncurses REQUIRED CONFIG)

add_executable(test_ncurses test_ncurses.c)
target_link_libraries(test_ncurses PRIVATE ncurses::ncurses)
