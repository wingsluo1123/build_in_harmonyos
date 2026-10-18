cmake_minimum_required(VERSION 3.20)
project(freerdp_consumer C CXX)

find_package(freerdp CONFIG REQUIRED)

add_executable(freerdp_consumer test.cpp)
target_link_libraries(freerdp_consumer PRIVATE freerdp::freerdp)
