cmake_minimum_required(VERSION 3.15)
project(test_gnome_desktop C)

find_package(gnome-desktop-3.0 REQUIRED)

add_executable(test_gnome_desktop src/test_gnome_desktop.c)
target_link_libraries(test_gnome_desktop PRIVATE
    gnome-desktop-3.0::gnome-desktop-3.0)

enable_testing()
add_test(NAME test_gnome_desktop COMMAND test_gnome_desktop)
