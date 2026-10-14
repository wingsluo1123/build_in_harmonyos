cmake_minimum_required(VERSION 3.15)
project(test_libcddb C)

find_package(libcddb REQUIRED)
add_executable(test_libcddb test.c)
target_link_libraries(test_libcddb PRIVATE libcddb::libcddb)
