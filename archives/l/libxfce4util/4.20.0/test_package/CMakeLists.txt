cmake_minimum_required(VERSION 3.15)
project(libxfce4util_consumer C)

find_package(libxfce4util CONFIG REQUIRED)

add_executable(libxfce4util_consumer test.c)
target_link_libraries(libxfce4util_consumer PRIVATE libxfce4util::libxfce4util)
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(libxfce4util_consumer PRIVATE -Wall -Wextra -Werror)
endif()
