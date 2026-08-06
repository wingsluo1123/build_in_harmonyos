cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_bad C)

# Find GStreamer via pkg-config
find_package(PkgConfig REQUIRED)
pkg_check_modules(GSTREAMER REQUIRED IMPORTED_TARGET gstreamer-1.0)
pkg_check_modules(GSTBASE REQUIRED IMPORTED_TARGET gstreamer-base-1.0)

# The codec parser library from gst-plugins-bad
pkg_check_modules(GSTCODECPARSERS REQUIRED IMPORTED_TARGET gstreamer-codecparsers-1.0)

add_executable(test_gst_plugins_bad test.c)
target_link_libraries(test_gst_plugins_bad
    PkgConfig::GSTREAMER
    PkgConfig::GSTBASE
    PkgConfig::GSTCODECPARSERS
)

enable_testing()
add_test(NAME test_gst_plugins_bad COMMAND test_gst_plugins_bad)
