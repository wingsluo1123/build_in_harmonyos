cmake_minimum_required(VERSION 3.15)
project(test_ipsumdump C)

# Create a minimal pcap file for testing (in-source, copied to build dir)
set(PCAP_SRC "${CMAKE_CURRENT_SOURCE_DIR}/test.pcap")

add_executable(test_ipsumdump test.c)

# The test binary is a verification harness that calls ipsumdump via system().
# No linking to the ipsumdump library is needed since ipsumdump is an application.

enable_testing()
add_test(NAME test_ipsumdump COMMAND test_ipsumdump WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

# Copy test.pcap to build directory so the test can find it
configure_file(${PCAP_SRC} ${CMAKE_CURRENT_BINARY_DIR}/test.pcap COPYONLY)
