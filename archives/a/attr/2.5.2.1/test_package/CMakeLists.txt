cmake_minimum_required(VERSION 3.15)
project(test_attr LANGUAGES C)

find_package(attr CONFIG REQUIRED)

add_executable(test_attr test.c)
target_link_libraries(test_attr PRIVATE attr::libattr)
