cmake_minimum_required(VERSION 3.15)
project(test_libadwaita C)

find_package(libadwaita-1 REQUIRED CONFIG)

add_executable(test_libadwaita test_libadwaita.c)
target_link_libraries(test_libadwaita PRIVATE libadwaita-1::libadwaita-1)
