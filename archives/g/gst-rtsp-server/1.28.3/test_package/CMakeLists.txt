cmake_minimum_required(VERSION 3.15)
project(test_gst_rtsp_server C)

# Find gst-rtsp-server via pkg-config (conan PkgConfigDeps generates .pc files)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GST_RTSP_SERVER REQUIRED gstreamer-rtsp-server-1.0)

add_executable(test_gst_rtsp_server test.c)
target_link_libraries(test_gst_rtsp_server ${GST_RTSP_SERVER_LIBRARIES})
target_include_directories(test_gst_rtsp_server PRIVATE ${GST_RTSP_SERVER_INCLUDE_DIRS})
target_compile_definitions(test_gst_rtsp_server PRIVATE ${GST_RTSP_SERVER_CFLAGS_OTHER})

enable_testing()
add_test(NAME test_gst_rtsp_server COMMAND test_gst_rtsp_server)
