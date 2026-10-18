cmake_minimum_required(VERSION 3.15)
project(xgks_consumer C)

find_package(xgks CONFIG REQUIRED)

add_executable(test_xgks test.c)
target_link_libraries(test_xgks PRIVATE xgks::xgks)
