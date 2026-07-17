cmake_minimum_required(VERSION 3.16)
project(test_qthttpserver CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Network)
find_package(qthttpserver REQUIRED CONFIG)
add_executable(test_qthttpserver test_qthttpserver.cpp)
target_link_libraries(test_qthttpserver PRIVATE Qt6::HttpServer Qt6::Core Qt6::Network)
