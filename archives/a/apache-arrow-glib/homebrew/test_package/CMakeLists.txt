cmake_minimum_required(VERSION 3.16)
project(test_arrow_glib C)

find_package(ArrowGLib REQUIRED)

add_executable(test_arrow_glib test_arrow_glib.c)
target_link_libraries(test_arrow_glib PRIVATE ArrowGLib::ArrowGLib)
