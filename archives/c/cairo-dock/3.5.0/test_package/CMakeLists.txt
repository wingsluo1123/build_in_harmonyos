cmake_minimum_required(VERSION 3.15)
project(test_cairo_dock C)

find_package(PkgConfig REQUIRED)

# Resolve exactly the modules cairo-dock's own build resolves, from the
# consumer side: gtk+-3.0 (the toolkit the dock is built on) and gldi (the
# pkg-config module the cairo-dock package itself installs).
pkg_check_modules(GTK3 REQUIRED IMPORTED_TARGET gtk+-3.0)
pkg_check_modules(GDI REQUIRED IMPORTED_TARGET gldi)

add_executable(test_cairo_dock test_cairo_dock.c)
target_link_libraries(test_cairo_dock PRIVATE PkgConfig::GDI PkgConfig::GTK3)
