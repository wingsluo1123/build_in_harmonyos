cmake_minimum_required(VERSION 3.15)
project(test_waffle C)

find_package(Waffle REQUIRED CONFIG)

add_executable(test_waffle test.c)
target_link_libraries(test_waffle Waffle::waffle)

enable_testing()
add_test(NAME test_waffle COMMAND test_waffle)
