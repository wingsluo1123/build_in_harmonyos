cmake_minimum_required(VERSION 3.15)
project(dbusmenu_smoke C)

find_package(dbusmenu-glib REQUIRED CONFIG)

add_executable(dbusmenu_smoke main.c)
target_link_libraries(dbusmenu_smoke PRIVATE dbusmenu-glib::dbusmenu-glib)

add_executable(dbusmenu_harmony harmony_tests/native_state.c)
target_link_libraries(dbusmenu_harmony PRIVATE dbusmenu-glib::dbusmenu-glib)
