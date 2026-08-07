cmake_minimum_required(VERSION 3.15)
project(test_pavucontrol C)

# This test verifies the pavucontrol binary is installed and executable
# by calling it with --version flag.
add_executable(test_pavucontrol test.c)
