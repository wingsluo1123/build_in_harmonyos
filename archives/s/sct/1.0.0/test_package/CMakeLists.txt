cmake_minimum_required(VERSION 3.15)
project(test_sct C)

# sct is a command line tool (no linkable library): the test runs the
# packaged binary and inspects its ELF platform markers.
add_executable(test_sct test.c)

enable_testing()
add_test(NAME test_sct COMMAND test_sct)
