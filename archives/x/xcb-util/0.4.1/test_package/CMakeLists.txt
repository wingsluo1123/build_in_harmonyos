cmake_minimum_required(VERSION 3.15)
project(test_xcb_util C)

if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(xcb-util REQUIRED)

add_executable(test_xcb_util test.c)
target_link_libraries(test_xcb_util PRIVATE xcb-util::xcb-util)

enable_testing()
add_test(NAME test_xcb_util COMMAND test_xcb_util)
