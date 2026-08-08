cmake_minimum_required(VERSION 3.15)
project(test_gtk4 C)

find_package(GTK4 REQUIRED CONFIG)

add_executable(test_gtk4 test_gtk4.c)
target_link_libraries(test_gtk4 PRIVATE GTK4::GTK4)
