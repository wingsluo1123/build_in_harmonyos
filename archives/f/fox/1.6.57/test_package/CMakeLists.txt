cmake_minimum_required(VERSION 3.15)
project(fox_consumer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(fox CONFIG REQUIRED)

add_executable(test_fox test_fox.cpp)
target_link_libraries(test_fox PRIVATE fox::fox)
