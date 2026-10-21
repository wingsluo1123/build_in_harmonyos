cmake_minimum_required(VERSION 3.15)
project(quesoglc_test C)

find_package(quesoglc CONFIG REQUIRED)

add_executable(test_quesoglc test_quesoglc.c)
target_link_libraries(test_quesoglc PRIVATE quesoglc::quesoglc)
