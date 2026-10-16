cmake_minimum_required(VERSION 3.15)
project(test_libbs2b C)

find_package(libbs2b REQUIRED)
add_executable(test_libbs2b test.c)
target_link_libraries(test_libbs2b PRIVATE libbs2b::libbs2b)
