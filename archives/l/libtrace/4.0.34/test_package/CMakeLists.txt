cmake_minimum_required(VERSION 3.15)
project(libtrace_consumer C)

find_package(libtrace REQUIRED)

add_executable(test_libtrace test_libtrace.c)
target_link_libraries(test_libtrace PRIVATE libtrace::libtrace)
