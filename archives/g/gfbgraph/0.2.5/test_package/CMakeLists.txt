cmake_minimum_required(VERSION 3.15)
project(test_gfbgraph C)

find_package(gfbgraph REQUIRED CONFIG)

add_executable(test_gfbgraph test_gfbgraph.c)
target_link_libraries(test_gfbgraph PRIVATE gfbgraph::gfbgraph)
