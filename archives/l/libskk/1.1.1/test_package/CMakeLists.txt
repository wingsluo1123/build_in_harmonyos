cmake_minimum_required(VERSION 3.15)
project(libskk_consumer LANGUAGES C)

find_package(libskk CONFIG REQUIRED)
add_executable(libskk_consumer test_package.c)
target_link_libraries(libskk_consumer PRIVATE libskk::libskk)