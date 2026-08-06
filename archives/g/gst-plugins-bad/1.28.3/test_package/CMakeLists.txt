cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_bad C)

# Use conan's CMakeDeps to find the package
find_package(gst-plugins-bad REQUIRED)

# Add system glib include paths (glib is a system dependency, not in conan)
include_directories(SYSTEM /storage/Users/currentUser/usr/local/include/glib-2.0)
include_directories(SYSTEM /storage/Users/currentUser/usr/local/lib/glib-2.0/include)

add_executable(test_gst_plugins_bad test_gst_plugins_bad.c)
target_link_libraries(test_gst_plugins_bad gst-plugins-bad::gst-plugins-bad)
