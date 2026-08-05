cmake_minimum_required(VERSION 3.15)
project(test_sndfile C)

find_package(SndFile REQUIRED CONFIG)

add_executable(test_sndfile test_sndfile.c)
target_link_libraries(test_sndfile PRIVATE SndFile::sndfile)
