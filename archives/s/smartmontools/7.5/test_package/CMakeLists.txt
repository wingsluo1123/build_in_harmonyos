cmake_minimum_required(VERSION 3.15)
project(test_smartmontools C)

# smartmontools is a CLI tool (smartctl, smartd), no library to link
add_executable(test_smartmontools test.c)

enable_testing()
add_test(NAME test_smartmontools COMMAND test_smartmontools)
