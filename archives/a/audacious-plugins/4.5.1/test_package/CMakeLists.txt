cmake_minimum_required(VERSION 3.15)
project(test_audacious-plugins C)

add_executable(test_audacious-plugins test.c)

# Link dl for dlopen
target_link_libraries(test_audacious-plugins ${CMAKE_DL_LIBS})
