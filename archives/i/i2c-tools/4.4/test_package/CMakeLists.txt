cmake_minimum_required(VERSION 3.15)
project(i2c_tools_consumer_test C)

find_package(i2c-tools CONFIG REQUIRED)

add_executable(test_i2c_api test_i2c_api.c)
target_link_libraries(test_i2c_api PRIVATE i2c-tools::i2c-tools)
