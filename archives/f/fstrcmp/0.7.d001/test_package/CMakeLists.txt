cmake_minimum_required(VERSION 3.15)
project(fstrcmp_smoke C)

find_package(fstrcmp REQUIRED CONFIG)

add_executable(fstrcmp_smoke main.c)
target_link_libraries(fstrcmp_smoke PRIVATE fstrcmp::fstrcmp)
