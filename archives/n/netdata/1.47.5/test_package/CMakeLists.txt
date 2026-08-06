cmake_minimum_required(VERSION 3.15)
project(test_netdata C)

# Minimal CMake for test_package structure (actual test runs in conanfile.py test())
add_executable(test_netdata test.c)
enable_testing()
add_test(NAME test_netdata COMMAND test_netdata)
