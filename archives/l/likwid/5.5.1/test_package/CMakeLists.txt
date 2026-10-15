cmake_minimum_required(VERSION 3.15)
project(likwid_consumer C)

find_package(likwid CONFIG REQUIRED)

add_executable(likwid_consumer test_consumer.c)
target_link_libraries(likwid_consumer PRIVATE likwid::likwid)

enable_testing()
add_test(NAME likwid_consumer COMMAND likwid_consumer)
