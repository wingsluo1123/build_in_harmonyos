cmake_minimum_required(VERSION 3.15)
project(test_seyon C)

# OHOS user toolchain (ohos.toolchain.cmake) sets
# CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY, which prevents find_package() from
# searching CMAKE_PREFIX_PATH (where conan 2's CMakeDeps generator drops the
# seyon-config.cmake). Override to BOTH so the conan generators directory is
# searched alongside the OHOS SDK native tree (libx11 test_package precedent).
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(seyon REQUIRED)

add_executable(test_seyon test_seyon.c)
target_link_libraries(test_seyon PRIVATE seyon::seyon)

enable_testing()
add_test(NAME test_seyon COMMAND test_seyon)
