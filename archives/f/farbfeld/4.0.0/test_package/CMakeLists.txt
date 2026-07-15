cmake_minimum_required(VERSION 3.15)
project(test_farbfeld C)

# This test helper generates a farbfeld image for pipe-based testing.
# The actual test is in conanfile.py's test() method which runs
# the installed farbfeld tools (ff2ppm, ff2pam) on the generated image.
add_executable(test_farbfeld test.c)
