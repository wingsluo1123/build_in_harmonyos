cmake_minimum_required(VERSION 3.15)
project(test_yara C)

find_package(yara REQUIRED)

add_executable(test_yara test.c)
target_link_libraries(test_yara yara::yara)
