cmake_minimum_required(VERSION 3.15)
project(test_dfc C)

# dfc is a CLI tool, not a library — just build a simple test
add_executable(test_dfc test.c)

enable_testing()
add_test(NAME test_dfc COMMAND test_dfc)
