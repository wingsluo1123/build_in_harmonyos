cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_bad C)

# Use conan's CMakeDeps to find the package
find_package(gst-plugins-bad REQUIRED)

# Dynamically find glib headers (system-installed via cmd-pkgs or meson subproject)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB IMPORTED_TARGET glib-2.0)
if(TARGET PkgConfig::GLIB)
    target_link_libraries(test_gst_plugins_bad PRIVATE PkgConfig::GLIB)
endif()

add_executable(test_gst_plugins_bad test_gst_plugins_bad.c)
target_link_libraries(test_gst_plugins_bad PRIVATE gst-plugins-bad::gst-plugins-bad)
