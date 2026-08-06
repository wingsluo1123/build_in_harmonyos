cmake_minimum_required(VERSION 3.15)
project(test_gst_rtsp_server C)

find_package(gst-rtsp-server REQUIRED CONFIG)
find_package(gstreamer REQUIRED CONFIG)

add_executable(test_gst_rtsp_server src/test_gst_rtsp_server.c)
target_link_libraries(test_gst_rtsp_server gst-rtsp-server::gstreamer-rtsp-server-1.0 gstreamer::gstreamer-1.0)
