cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_base C)

find_package(gst-plugins-base REQUIRED)
find_package(gstreamer REQUIRED)
find_package(glib REQUIRED)

add_executable(test_gst_plugins_base test_gst_plugins_base.c)
target_link_libraries(test_gst_plugins_base gst-plugins-base::gst-plugins-base gstreamer::gstreamer glib::glib)
