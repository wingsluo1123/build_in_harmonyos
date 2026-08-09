cmake_minimum_required(VERSION 3.15)
project(test_s2n C)

find_package(s2n REQUIRED)

add_executable(test_s2n test.c)
target_link_libraries(test_s2n AWS::s2n)

enable_testing()
add_test(NAME test_s2n COMMAND test_s2n)
