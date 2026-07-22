cmake_minimum_required(VERSION 3.15)
project(test_sdl3_mixer C)

find_package(sdl3_mixer REQUIRED)

add_executable(test_sdl3_mixer test.c)
target_link_libraries(test_sdl3_mixer sdl3_mixer::sdl3_mixer)

enable_testing()
add_test(NAME test_sdl3_mixer COMMAND test_sdl3_mixer)
