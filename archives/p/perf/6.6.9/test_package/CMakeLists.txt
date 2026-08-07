cmake_minimum_required(VERSION 3.15)
project(test_perf C)

# Simple test that verifies perf binary exists and can report its version
add_executable(test_perf test_perf.c)

# Link against the perf package's bin directory
# The test just checks the binary exists and runs --version
