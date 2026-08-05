cmake_minimum_required(VERSION 3.15)
project(test_sndfile C)

find_package(SndFile CONFIG REQUIRED)

add_executable(test_sndfile test_sndfile.c)
target_link_libraries(test_sndfile SndFile::sndfile)

enable_testing()
add_test(NAME test_sndfile COMMAND test_sndfile)
