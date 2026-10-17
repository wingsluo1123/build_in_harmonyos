cmake_minimum_required(VERSION 3.15)
project(test_libidn C)

find_package(libidn REQUIRED)

add_executable(test_libidn test.c)
target_link_libraries(test_libidn libidn::libidn)
