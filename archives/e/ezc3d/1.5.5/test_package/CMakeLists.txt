cmake_minimum_required(VERSION 3.15)
project(ezc3d_consumer_test CXX)

find_package(ezc3d CONFIG REQUIRED)

add_executable(ezc3d_consumer_test consumer_e2e.cpp)
target_link_libraries(ezc3d_consumer_test PRIVATE ezc3d::ezc3d)
set_target_properties(ezc3d_consumer_test PROPERTIES
    CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
