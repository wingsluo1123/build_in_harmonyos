cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_base C)

find_package(gst-plugins-base REQUIRED CONFIG)
find_package(gstreamer REQUIRED CONFIG)

add_executable(test_gst_plugins_base src/test_gst_plugins_base.c)
target_link_libraries(test_gst_plugins_base gst-plugins-base::gstreamer-app-1.0 gst-plugins-base::gstreamer-pbutils-1.0 gstreamer::gstreamer-1.0)
