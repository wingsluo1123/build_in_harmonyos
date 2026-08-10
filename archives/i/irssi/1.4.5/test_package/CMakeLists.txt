cmake_minimum_required(VERSION 3.15)
project(test_irssi C)

# irssi is an application (CLI tool), not a library.
# test.c calls system("irssi --version") to verify the binary works.
# The conanfile.py test() also runs irssi --version directly.

add_executable(test_irssi test.c)

enable_testing()
add_test(NAME test_irssi COMMAND test_irssi)
