cmake_minimum_required(VERSION 3.15)
project(test_mapserver C)

find_package(mapserver CONFIG REQUIRED)

add_executable(test_mapserver test_mapserver.c)
target_link_libraries(test_mapserver PRIVATE mapserver::mapserver)
