cmake_minimum_required(VERSION 3.15)
project(test_gstreamer C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GST IMPORTED_TARGET gstreamer-1.0)

add_executable(test_gstreamer test.c)
target_link_libraries(test_gstreamer PkgConfig::GST)

enable_testing()
add_test(NAME test_gstreamer COMMAND test_gstreamer)
