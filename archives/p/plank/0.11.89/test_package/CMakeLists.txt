cmake_minimum_required(VERSION 3.15)
project(test_plank C)

find_package(plank REQUIRED)

add_executable(test_plank test_plank.c)
target_link_libraries(test_plank plank::plank)
