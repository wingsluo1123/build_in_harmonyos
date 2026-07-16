cmake_minimum_required(VERSION 3.15)
project(test_knock C)

find_package(knock REQUIRED)

add_executable(test_knock test.c)
target_link_libraries(test_knock knock::knock)

enable_testing()
add_test(NAME test_knock COMMAND test_knock)