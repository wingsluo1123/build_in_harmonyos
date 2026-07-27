cmake_minimum_required(VERSION 3.16)
project(test_vapoursynth C)

find_package(vapoursynth CONFIG REQUIRED)

add_executable(test_vapoursynth test_vapoursynth.c)
target_link_libraries(test_vapoursynth PRIVATE vapoursynth::vapoursynth)
