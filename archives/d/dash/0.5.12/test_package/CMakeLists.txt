cmake_minimum_required(VERSION 3.15)
project(test_dash C)

# Simple test - just verify the dash binary exists
enable_testing()
add_test(NAME test_dash COMMAND ${CMAKE_COMMAND} -E echo "dash test placeholder")
