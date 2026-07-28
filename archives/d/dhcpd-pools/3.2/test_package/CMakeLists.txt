cmake_minimum_required(VERSION 3.15)
project(test_dhcpd-pools C)

add_executable(test_dhcpd-pools test.c)
target_link_libraries(test_dhcpd-pools)

# Copy test data to build dir for offline smoke test
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/dhcpd.conf ${CMAKE_CURRENT_BINARY_DIR}/dhcpd.conf COPYONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/dhcpd.leases ${CMAKE_CURRENT_BINARY_DIR}/dhcpd.leases COPYONLY)
