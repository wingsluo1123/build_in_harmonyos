cmake_minimum_required(VERSION 3.15)
project(test_gstreamer C)

# Find the package via Conan-generated CMakeDeps
find_package(GStreamer REQUIRED)

add_executable(test_gstreamer test.c)
target_link_libraries(test_gstreamer GStreamer::GStreamer)

enable_testing()
add_test(NAME test_gstreamer COMMAND test_gstreamer)
