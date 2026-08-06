cmake_minimum_required(VERSION 3.10)
project(test_ffmpeg2theora C)

# Simple test program — the actual test runs ffmpeg2theora --help
# in the conanfile.py test() method (R34: execute the binary)
add_executable(test_ffmpeg2theora test.c)
