cmake_minimum_required(VERSION 3.15)
project(PackageTest C)

find_package(gst-plugins-base REQUIRED COMPONENTS gstreamer-pbutils-1.0)
find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gst_base test_gst_base.c)
target_link_libraries(test_gst_base gst-plugins-base::gstreamer-pbutils-1.0 gstreamer::gstreamer glib2::glib2)

enable_testing()
add_test(NAME test_gst_base COMMAND test_gst_base)
