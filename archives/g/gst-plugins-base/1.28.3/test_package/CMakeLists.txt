cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_base C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GST_APP IMPORTED_TARGET gstreamer-app-1.0)

add_executable(test_gst_plugins_base test.c)
target_link_libraries(test_gst_plugins_base PkgConfig::GST_APP)

enable_testing()
add_test(NAME test_gst_plugins_base COMMAND test_gst_plugins_base)
