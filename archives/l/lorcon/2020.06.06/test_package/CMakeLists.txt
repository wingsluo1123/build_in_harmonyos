cmake_minimum_required(VERSION 3.15)
project(lorcon_test C)

find_package(lorcon CONFIG REQUIRED)

add_executable(lorcon_test test.c)
target_link_libraries(lorcon_test PRIVATE lorcon::lorcon)

enable_testing()
add_test(NAME lorcon_api COMMAND lorcon_test)
