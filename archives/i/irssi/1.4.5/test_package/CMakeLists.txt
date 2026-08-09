cmake_minimum_required(VERSION 3.15)
project(test_irssi C)

# irssi is an application (CLI tool), not a library.
# The test_package just builds a trivial binary and the conanfile.py test()
# runs the installed irssi --version to verify functionality.

add_executable(test_irssi test.c)

enable_testing()
add_test(NAME test_irssi COMMAND test_irssi)
