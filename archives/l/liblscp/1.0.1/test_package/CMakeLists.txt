cmake_minimum_required(VERSION 3.15)
project(test_liblscp C)

find_package(liblscp REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_liblscp test_liblscp.c)
target_link_libraries(test_liblscp PRIVATE liblscp::liblscp Threads::Threads)
