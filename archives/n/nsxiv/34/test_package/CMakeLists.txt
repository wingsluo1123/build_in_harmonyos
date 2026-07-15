cmake_minimum_required(VERSION 3.16)
project(test_nsxiv C)

# Test executable - verifies nsxiv binary is valid ELF
add_executable(test_nsxiv test_nsxiv.c)

# The nsxiv binary path is passed as a command-line argument in ctest
enable_testing()
add_test(NAME nsxiv_binary_test
         COMMAND test_nsxiv $ENV{NSXIV_BIN}
         WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
