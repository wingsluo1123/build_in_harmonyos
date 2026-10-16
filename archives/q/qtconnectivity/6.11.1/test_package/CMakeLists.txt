cmake_minimum_required(VERSION 3.16)
project(test_qtconnectivity CXX)

find_package(Qt6 REQUIRED COMPONENTS Bluetooth Nfc)

add_executable(test_qtconnectivity test_qtconnectivity.cpp)
target_link_libraries(test_qtconnectivity PRIVATE Qt6::Bluetooth Qt6::Nfc)
