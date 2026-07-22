cmake_minimum_required(VERSION 3.15)
project(test_sdl3_ttf C)

find_package(sdl3_ttf REQUIRED)

add_executable(test_sdl3_ttf test.c)
target_link_libraries(test_sdl3_ttf sdl3_ttf::sdl3_ttf)

enable_testing()
add_test(NAME test_sdl3_ttf COMMAND test_sdl3_ttf)
