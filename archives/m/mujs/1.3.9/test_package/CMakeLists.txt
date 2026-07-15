cmake_minimum_required(VERSION 3.15)
project(test_mujs C)

find_package(mujs REQUIRED)

add_executable(test_mujs test.c)
target_link_libraries(test_mujs mujs::mujs)

enable_testing()
add_test(NAME test_mujs COMMAND test_mujs)
