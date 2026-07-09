cmake_minimum_required(VERSION 3.15)
project(test_gmp C)

find_package(GMP REQUIRED)

add_executable(test_gmp test_gmp.c)
target_link_libraries(test_gmp GMP::GMP)