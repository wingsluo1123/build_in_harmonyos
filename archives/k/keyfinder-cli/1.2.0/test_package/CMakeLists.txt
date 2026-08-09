cmake_minimum_required(VERSION 3.15)
project(test_keyfinder_cli)

# Simple test that just compiles and links successfully
# The actual test (running keyfinder-cli --help) is done in conanfile.py test()
add_executable(test_keyfinder_cli test.cpp)

enable_testing()
add_test(NAME keyfinder_cli_test COMMAND test_keyfinder_cli)
