cmake_minimum_required(VERSION 3.15)
project(test_gst_libav C)

# R34: Test must actually depend on the tested package.
# gst-libav is a GStreamer plugin (.so) loaded at runtime.
# We use dlopen to load and verify the plugin has GStreamer symbols.
# The plugin path is provided via the conan package's libdirs.

add_executable(test_gst_libav test.c)
target_link_libraries(test_gst_libav ${CMAKE_DL_LIBS})

# Plugin path is provided at runtime via GST_LIBAV_PLUGIN_PATH env var
# (set by test_package/conanfile.py test() method)

enable_testing()
add_test(NAME test_gst_libav COMMAND test_gst_libav)
