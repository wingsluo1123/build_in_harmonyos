cmake_minimum_required(VERSION 3.15)
project(test_readline C)

find_package(readline REQUIRED)

add_executable(test_readline test.c)
target_link_libraries(test_readline readline::readline)

enable_testing()
add_test(NAME test_readline COMMAND test_readline)
