cmake_minimum_required(VERSION 3.15)
project(test_xeus_zmq CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(xeus-zmq REQUIRED CONFIG)

add_executable(test_xeus_zmq test.cpp)
target_link_libraries(test_xeus_zmq PRIVATE xeus-zmq)

enable_testing()
add_test(NAME test_xeus_zmq COMMAND test_xeus_zmq)
