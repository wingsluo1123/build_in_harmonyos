cmake_minimum_required(VERSION 3.16)
project(test_libcopp CXX)

find_package(libcopp REQUIRED CONFIG)

add_executable(test_libcopp test_libcopp.cpp)
target_link_libraries(test_libcopp PRIVATE libcopp::copp)
# 上游默认用 C++14 起步；本消费者只验证打包产物的头文件与链接面。
set_property(TARGET test_libcopp PROPERTY CXX_STANDARD 14)
set_property(TARGET test_libcopp PROPERTY CXX_STANDARD_REQUIRED ON)
