cmake_minimum_required(VERSION 3.15)
project(test_iperf C)

# Build and run the iperf binary verification test.
# The test calls system("iperf --version") to verify the binary is installed.
add_executable(test_iperf test.c)
enable_testing()
add_test(NAME test_iperf COMMAND test_iperf)
