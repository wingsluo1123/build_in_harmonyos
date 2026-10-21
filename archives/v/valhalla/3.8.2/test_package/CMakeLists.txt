cmake_minimum_required(VERSION 3.15)
project(valhalla_consumer CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(valhalla CONFIG REQUIRED)

add_executable(test_valhalla test_valhalla.cpp)
target_link_libraries(test_valhalla PRIVATE valhalla::valhalla)
