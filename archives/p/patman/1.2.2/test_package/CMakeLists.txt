cmake_minimum_required(VERSION 3.15)
project(test_patman CXX)

# 消费者程序本身不链接 patman；patman 的输出（命中表）是它的输入。
add_executable(check_hits check_hits.cpp)
