cmake_minimum_required(VERSION 3.15)
project(test_datamash C)

# datamash is a CLI tool, no library to link against
# Test is done via conanfile.py test() method

enable_testing()
add_custom_target(test_datamash ALL
    COMMAND ${CMAKE_COMMAND} -E echo "datamash test skipped (tool-only package)")
add_test(NAME test_datamash COMMAND ${CMAKE_COMMAND} -E echo "ok")
