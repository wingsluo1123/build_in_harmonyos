cmake_minimum_required(VERSION 3.15)
project(test_geos LANGUAGES C)

find_package(GEOS CONFIG REQUIRED)

add_executable(test_geos test_geos.c)
target_link_libraries(test_geos PRIVATE GEOS::geos_c)
