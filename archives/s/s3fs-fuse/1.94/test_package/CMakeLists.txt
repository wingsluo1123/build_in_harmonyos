cmake_minimum_required(VERSION 3.15)
project(test_s3fs-fuse C)

# s3fs-fuse is a command-line application, not a library.
# This test verifies the binary is available and runnable.
# The actual binary execution is done in conanfile.py test() method.
add_executable(test_s3fs-fuse test.c)
