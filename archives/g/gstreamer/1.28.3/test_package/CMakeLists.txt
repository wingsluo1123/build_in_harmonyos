cmake_minimum_required(VERSION 3.15)
project(test_gstreamer C)

find_package(gstreamer REQUIRED CONFIG)

add_executable(test_gstreamer src/test_gstreamer.c)
target_link_libraries(test_gstreamer gstreamer::gstreamer-1.0)

enable_testing()
add_test(NAME test_gstreamer COMMAND test_gstreamer)
