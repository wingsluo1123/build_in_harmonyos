cmake_minimum_required(VERSION 3.15)
project(test_physfs C)

find_package(PhysFS REQUIRED CONFIG)
add_executable(test_physfs test_physfs.c)
target_link_libraries(test_physfs PRIVATE PhysFS::PhysFS)
