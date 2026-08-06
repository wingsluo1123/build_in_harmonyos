cmake_minimum_required(VERSION 3.15)
project(test_htop C)

# htop is an application package (package_type="application")
# The test uses PATH (via conanrun env) to find htop, not CMake linking
add_executable(test_htop test.c)

enable_testing()
add_test(NAME test_htop COMMAND test_htop)
