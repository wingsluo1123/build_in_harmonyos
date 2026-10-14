cmake_minimum_required(VERSION 3.15)
project(test_mbedtls3 C)

find_package(mbedtls-3 REQUIRED CONFIG)

add_executable(test_mbedtls test.c)
target_link_libraries(test_mbedtls PRIVATE mbedtls-3::mbedtls-3)
