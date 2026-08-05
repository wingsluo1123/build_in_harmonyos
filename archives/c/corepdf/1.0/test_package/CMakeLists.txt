cmake_minimum_required(VERSION 3.15)
project(test_corepdf LANGUAGES CXX)

# Simple test that verifies the corepdf binary is installed
# and attempts to run it (headless systems may fail at Qt init, which is OK)
add_executable(test_corepdf test_corepdf.cpp)
