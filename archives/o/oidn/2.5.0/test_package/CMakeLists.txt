cmake_minimum_required(VERSION 3.15)
project(test_oidn C)

find_package(OpenImageDenoise REQUIRED)

add_executable(test_oidn test_oidn.c)
target_link_libraries(test_oidn OpenImageDenoise::OpenImageDenoise)
