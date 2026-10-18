cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(totem-pl REQUIRED)
find_package(GLib REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE totem-pl::plparser
                                          GLib::GLib
                                          GLib::GObject
                                          GLib::Gio)
