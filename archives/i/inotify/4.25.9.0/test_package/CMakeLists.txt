cmake_minimum_required(VERSION 3.15)
project(inotify_consumer CXX)

find_package(inotify CONFIG REQUIRED)

add_executable(test_inotify test_inotify.cpp)
target_link_libraries(test_inotify PRIVATE inotify::inotifytools)
