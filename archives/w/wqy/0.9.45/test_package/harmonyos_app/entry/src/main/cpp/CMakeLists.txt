cmake_minimum_required(VERSION 3.16)
project(wqyfontprobe LANGUAGES CXX)

add_library(wqyfontprobe SHARED napi_init.cpp)
target_compile_features(wqyfontprobe PRIVATE cxx_std_17)
target_include_directories(wqyfontprobe PRIVATE "${CMAKE_SYSROOT}/usr/include/native_drawing")
target_link_libraries(wqyfontprobe PRIVATE libace_napi.z.so libnative_drawing.so)
