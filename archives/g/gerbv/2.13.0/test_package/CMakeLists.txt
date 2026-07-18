cmake_minimum_required(VERSION 3.15)
project(test_gerbv C)

# R34: Test must substantially depend on the tested package
# This test verifies gerbv binary works
find_program(GERBV_BIN gerbv REQUIRED)
enable_testing()
add_test(NAME test_gerbv_version COMMAND gerbv --version)
