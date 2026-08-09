cmake_minimum_required(VERSION 3.15)
project(test_hwinfo C)

# Find the hwinfo package provided by Conan
find_package(hwinfo REQUIRED)

add_executable(test_hwinfo test.c)
target_link_libraries(test_hwinfo PRIVATE hwinfo::hwinfo)
