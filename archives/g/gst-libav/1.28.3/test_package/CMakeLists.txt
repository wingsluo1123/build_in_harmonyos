cmake_minimum_required(VERSION 3.15)
project(test_gst_libav C)

# R34: Test must actually depend on the tested package.
# gst-libav is a GStreamer plugin (.so) loaded at runtime.
# We use dlopen to load and verify the plugin has GStreamer symbols.
# The plugin path is provided via the conan package's libdirs.

add_executable(test_gst_libav test.c)
target_link_libraries(test_gst_libav ${CMAKE_DL_LIBS})

# Set the plugin path from conan-generated info
# The gst-libav package installs to lib/gstreamer-1.0/
target_compile_definitions(test_gst_libav PRIVATE
    GST_LIBAV_PLUGIN_PATH="${CMAKE_CURRENT_SOURCE_DIR}/../../lib/gstreamer-1.0"
)

enable_testing()
add_test(NAME test_gst_libav COMMAND test_gst_libav)
