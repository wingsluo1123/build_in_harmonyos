cmake_minimum_required(VERSION 3.15)
project(test_lilv C)

find_package(lilv CONFIG REQUIRED)

add_executable(test_lilv test_lilv.c)
target_link_libraries(test_lilv PRIVATE lilv::lilv)
