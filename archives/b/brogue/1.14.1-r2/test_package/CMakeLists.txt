cmake_minimum_required(VERSION 3.15)
project(test_brogue C)

# brogue is a CLI tool (application), not a library — do NOT link against it.
# See bitwise/0.50/test_package/CMakeLists.txt for the project pattern.

enable_testing()
add_test(NAME test_brogue COMMAND test_brogue)
