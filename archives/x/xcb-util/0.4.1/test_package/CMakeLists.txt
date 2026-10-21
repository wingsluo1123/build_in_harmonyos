cmake_minimum_required(VERSION 3.15)
project(test_xcb_util C)

if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(xcb-util REQUIRED)
find_package(libxcb REQUIRED)

# Generic consumer test: pure helpers + ABI pins (no X server needed).
add_executable(test_xcb_util test.c)
target_link_libraries(test_xcb_util PRIVATE
    xcb-util::xcb-util
    libxcb::libxcb)

# OHOS-specific port test: __OHOS__ guard, versioned soname and the exact
# ELF DT_NEEDED link closure of the produced shared library.
add_executable(test_ohos_port test_ohos_port.c)
target_link_libraries(test_ohos_port PRIVATE
    xcb-util::xcb-util
    libxcb::libxcb)

enable_testing()
add_test(NAME test_xcb_util COMMAND test_xcb_util)
add_test(NAME test_ohos_port COMMAND test_ohos_port)
