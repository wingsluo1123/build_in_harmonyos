cmake_minimum_required(VERSION 3.16)
project(qt5charts_test CXX)

find_package(Qt5Charts REQUIRED)

add_executable(qt5charts_test test.cpp)
target_link_libraries(qt5charts_test Qt5::Charts)
