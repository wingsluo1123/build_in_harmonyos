cmake_minimum_required(VERSION 3.15)
project(levmar-test LANGUAGES C)

find_package(levmar CONFIG REQUIRED)

add_executable(levmar_test test_levmar.c)
target_link_libraries(levmar_test PRIVATE levmar::levmar)
