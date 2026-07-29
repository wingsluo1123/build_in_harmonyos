cmake_minimum_required(VERSION 3.15)
project(test_libmaxminddb LANGUAGES C)

find_package(maxminddb CONFIG REQUIRED)

add_executable(test_libmaxminddb test_libmaxminddb.c)
target_link_libraries(test_libmaxminddb PRIVATE maxminddb::maxminddb)
