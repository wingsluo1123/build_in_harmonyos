cmake_minimum_required(VERSION 3.15)
project(PackageTest C)

find_package(gst-plugins-good REQUIRED)
find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gst_good test_gst_good.c)
target_link_libraries(test_gst_good gst-plugins-good::gst-plugins-good gstreamer::gstreamer glib2::glib2)

# Set GST_PLUGIN_PATH to find plugins
set_target_properties(test_gst_good PROPERTIES
    ENVIRONMENT "GST_PLUGIN_PATH=$<TARGET_FILE_DIR:gst-plugins-good::gst-plugins-good>")

enable_testing()
add_test(NAME test_gst_good COMMAND test_gst_good)
