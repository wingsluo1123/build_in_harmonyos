cmake_minimum_required(VERSION 3.15)
project(test_libsoundio LANGUAGES C)

find_package(SoundIo CONFIG REQUIRED)

add_executable(test_libsoundio test_libsoundio.c)
target_link_libraries(test_libsoundio PRIVATE SoundIo::soundio)
