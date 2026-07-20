cmake_minimum_required(VERSION 3.15)
project(test_glib C)

find_package(glib REQUIRED CONFIG)

add_executable(test_glib test_glib.c)
target_link_libraries(test_glib PRIVATE glib::glib)
