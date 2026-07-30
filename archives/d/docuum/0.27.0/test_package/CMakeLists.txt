cmake_minimum_required(VERSION 3.15)
project(docuum_test LANGUAGES NONE)

include(GNUInstallDirs)

# No library to link; the binary is tested via conanfile.py's test()
# This file exists to satisfy the test_package skeleton convention.
