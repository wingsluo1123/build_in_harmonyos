cmake_minimum_required(VERSION 3.15)
project(test_proj LANGUAGES CXX)

find_package(PROJ CONFIG REQUIRED)

add_executable(test_proj test_proj.cpp)
target_link_libraries(test_proj PRIVATE PROJ::proj)
