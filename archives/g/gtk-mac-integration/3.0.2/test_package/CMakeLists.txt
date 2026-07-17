cmake_minimum_required(VERSION 3.15)
project(gtk_mac_integration_test LANGUAGES C)

find_package(gtk-mac-integration REQUIRED CONFIG)
add_executable(test_package test_package.c)
target_link_libraries(
    test_package PRIVATE gtk-mac-integration::gtk-mac-integration
)
