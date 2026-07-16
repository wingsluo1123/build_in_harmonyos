cmake_minimum_required(VERSION 3.15)
project(test_bento4 C)

find_package(ap4 REQUIRED)

add_executable(test_bento4 test.c)
target_link_libraries(test_bento4 ap4)

enable_testing()
add_test(NAME test_bento4 COMMAND test_bento4)