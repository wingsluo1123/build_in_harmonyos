cmake_minimum_required(VERSION 3.15)
project(test_rstatd C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(test_rstatd test_rstatd.c)
