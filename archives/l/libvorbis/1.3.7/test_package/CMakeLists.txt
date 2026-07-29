cmake_minimum_required(VERSION 3.15)
project(libvorbis_test_package LANGUAGES C)

find_package(Vorbis REQUIRED CONFIG)

add_executable(test_libvorbis test_libvorbis.c)
target_link_libraries(
    test_libvorbis
    PRIVATE
        Vorbis::vorbis
        Vorbis::vorbisenc
        Vorbis::vorbisfile
)
