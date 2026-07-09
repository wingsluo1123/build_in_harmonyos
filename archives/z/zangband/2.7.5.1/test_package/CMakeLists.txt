cmake_minimum_required(VERSION 3.15)
project(test_zangband C)

# Zangband is a binary, not a library — no find_package needed
add_executable(test_zangband test.c)

enable_testing()
add_test(NAME test_zangband COMMAND test_zangband)
