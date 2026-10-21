cmake_minimum_required(VERSION 3.15)
project(test_libdisplay_info C)

find_package(libdisplay-info REQUIRED)

add_executable(test_libdisplay_info test.c)
target_link_libraries(test_libdisplay_info libdisplay-info::libdisplay-info)

enable_testing()
add_test(NAME test_libdisplay_info COMMAND test_libdisplay_info)
