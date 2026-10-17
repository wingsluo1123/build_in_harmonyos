cmake_minimum_required(VERSION 3.15)
project(imagination_consumer_test C)

add_executable(imagination_consumer_test imagination_consumer_test.c)
target_link_libraries(imagination_consumer_test ${CMAKE_DL_LIBS})
