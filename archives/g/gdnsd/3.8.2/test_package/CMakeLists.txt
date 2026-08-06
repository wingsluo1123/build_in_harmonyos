cmake_minimum_required(VERSION 3.15)
project(test_gdnsd C)

add_executable(test_gdnsd test.c)

enable_testing()
add_test(NAME test_gdnsd COMMAND test_gdnsd)
