cmake_minimum_required(VERSION 3.15)
project(test_amrwb C)

find_package(opencore-amrwb REQUIRED)

add_executable(test_amrwb test_amrwb.c)
target_link_libraries(test_amrwb opencore_amrwb::opencore_amrwb)

enable_testing()
add_test(NAME test_amrwb COMMAND test_amrwb)
