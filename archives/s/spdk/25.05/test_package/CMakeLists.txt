cmake_minimum_required(VERSION 3.15)
project(spdk_consumer C)

find_package(spdk CONFIG REQUIRED)

add_executable(test_spdk test_spdk.c)
target_link_libraries(test_spdk PRIVATE spdk::spdk)
