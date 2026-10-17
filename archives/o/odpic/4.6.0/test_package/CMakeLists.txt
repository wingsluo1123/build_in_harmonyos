cmake_minimum_required(VERSION 3.15)
project(test_odpic C)

set(CMAKE_C_STANDARD 11)

find_package(dpi REQUIRED CONFIG)

add_executable(test_odpic test.c)
target_link_libraries(test_odpic PRIVATE dpi::odpic)

enable_testing()
add_test(NAME test_odpic COMMAND test_odpic)
