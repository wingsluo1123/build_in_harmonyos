cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(sndio CONFIG REQUIRED)

add_executable(test_sndio test_sndio.c)
target_link_libraries(test_sndio PRIVATE sndio::sndio)
