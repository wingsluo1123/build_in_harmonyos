cmake_minimum_required(VERSION 3.15)
project(test_live555 CXX)

find_package(live555 REQUIRED)
add_executable(test_live555 test.cpp)
target_link_libraries(test_live555 PRIVATE live555::live555)
