cmake_minimum_required(VERSION 3.15)
project(test_lirc CXX)

find_package(lirc REQUIRED CONFIG)

add_executable(test_lirc test_lirc.cpp)
target_link_libraries(test_lirc PRIVATE lirc::lirc)
