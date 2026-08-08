cmake_minimum_required(VERSION 3.15)
project(test_xfce4-pulseaudio-plugin C)

add_executable(test_xfce4-pulseaudio-plugin test.c)
target_link_libraries(test_xfce4-pulseaudio-plugin ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_xfce4-pulseaudio-plugin COMMAND test_xfce4-pulseaudio-plugin)
