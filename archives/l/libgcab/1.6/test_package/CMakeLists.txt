cmake_minimum_required(VERSION 3.15)
project(test_libgcab C)

find_package(libgcab REQUIRED)
find_package(glib REQUIRED)
find_package(zlib REQUIRED)

add_executable(test_libgcab src/test_libgcab.c)
target_link_libraries(test_libgcab libgcab::libgcab glib::glib)
