cmake_minimum_required(VERSION 3.15)
project(test_nettle C)

find_package(Nettle REQUIRED)

add_executable(test_nettle test_nettle.c)
target_link_libraries(test_nettle Nettle::Nettle)