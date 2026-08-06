cmake_minimum_required(VERSION 3.15)
project(test_minizip_ng LANGUAGES C)

find_package(minizip REQUIRED)

add_executable(test_minizip_ng test_minizip_ng.c)
target_link_libraries(test_minizip_ng PRIVATE minizip::minizip)

enable_testing()
add_test(NAME minizip_ng_test COMMAND test_minizip_ng)
