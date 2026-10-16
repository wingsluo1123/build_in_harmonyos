cmake_minimum_required(VERSION 3.15)
project(netpbm_test C)

find_package(netpbm REQUIRED CONFIG)

add_executable(test_netpbm test.c)
target_link_libraries(test_netpbm PRIVATE netpbm::netpbm)

enable_testing()
add_test(NAME netpbm_api
         COMMAND test_netpbm "${CMAKE_CURRENT_BINARY_DIR}/sample.pam")
