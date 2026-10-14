cmake_minimum_required(VERSION 3.15)
project(shuffle C)

add_executable(shuffle shuffle.c)
install(TARGETS shuffle RUNTIME DESTINATION bin)
