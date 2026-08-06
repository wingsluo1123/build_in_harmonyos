cmake_minimum_required(VERSION 3.15)
project(test_gstreamer C)

find_package(gstreamer REQUIRED)
find_package(glib REQUIRED)

add_executable(test_gstreamer test_gstreamer.c)
target_link_libraries(test_gstreamer gstreamer::gstreamer glib::glib)

enable_testing()
add_test(NAME test_gstreamer COMMAND test_gstreamer)
