cmake_minimum_required(VERSION 3.15)
project(test_bear C)

# Build a simple test binary to verify package integrity
add_executable(test_bear test_bear.c)

# The actual bear --version test is run via conanfile.py test() method
enable_testing()
add_test(NAME bear_version_test COMMAND test_bear)
