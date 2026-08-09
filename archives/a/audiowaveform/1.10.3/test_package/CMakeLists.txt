cmake_minimum_required(VERSION 3.15)
project(test_audiowaveform C)

# Build placeholder test binary (real test runs via conanfile.py test())
add_executable(test_audiowaveform test.c)
