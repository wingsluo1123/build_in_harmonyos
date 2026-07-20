cmake_minimum_required(VERSION 3.15)
project(test_gdk-pixbuf C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GDK_PIXBUF IMPORTED_TARGET gdk-pixbuf-2.0)

add_executable(test_gdk-pixbuf test.c)
target_link_libraries(test_gdk-pixbuf PkgConfig::GDK_PIXBUF)

enable_testing()
add_test(NAME test_gdk-pixbuf COMMAND test_gdk-pixbuf)
