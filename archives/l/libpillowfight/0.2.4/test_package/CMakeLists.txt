cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libpillowfight REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer libpillowfight::libpillowfight)

add_executable(test_harmonyos test_harmonyos.c)
target_link_libraries(test_harmonyos libpillowfight::libpillowfight)
