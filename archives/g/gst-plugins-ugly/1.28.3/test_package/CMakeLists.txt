cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_ugly C)

find_package(gstreamer REQUIRED)
find_package(glib REQUIRED)

add_executable(test_gst_plugins_ugly test_gst_plugins_ugly.c)
target_link_libraries(test_gst_plugins_ugly gstreamer::gstreamer glib::glib)
