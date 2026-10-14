cmake_minimum_required(VERSION 3.16)
project(test_libglvnd C)

find_package(libglvnd CONFIG REQUIRED)

add_executable(test_libglvnd test_libglvnd.c)
target_link_libraries(test_libglvnd PRIVATE libglvnd::libglvnd)
