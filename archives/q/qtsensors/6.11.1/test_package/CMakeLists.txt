cmake_minimum_required(VERSION 3.16)
project(test_qtsensors CXX)

find_package(Qt6 REQUIRED COMPONENTS Sensors)

add_executable(test_qtsensors test_qtsensors.cpp)
target_link_libraries(test_qtsensors PRIVATE Qt6::Sensors)
