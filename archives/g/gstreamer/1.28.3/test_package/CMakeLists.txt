cmake_minimum_required(VERSION 3.15)
project(PackageTest C)

find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gst test_gst.c)
target_link_libraries(test_gst gstreamer::gstreamer glib2::glib2)

enable_testing()
add_test(NAME test_gst COMMAND test_gst)
