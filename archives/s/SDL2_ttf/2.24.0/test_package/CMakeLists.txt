cmake_minimum_required(VERSION 3.15)
project(test_sdl2_ttf LANGUAGES C)

find_package(SDL2_ttf CONFIG REQUIRED)

add_executable(test_sdl2_ttf test_sdl2_ttf.c)
target_link_libraries(test_sdl2_ttf PRIVATE SDL2_ttf::SDL2_ttf)
