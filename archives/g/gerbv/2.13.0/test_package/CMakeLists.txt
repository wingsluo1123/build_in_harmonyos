cmake_minimum_required(VERSION 3.15)
project(test_gerbv C)

# R34: Test must substantially depend on the tested package
# This test compiles test.c which verifies gerbv binary works
enable_testing()

add_executable(test_gerbv test.c)
add_test(NAME test_gerbv_version COMMAND test_gerbv)
