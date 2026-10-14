cmake_minimum_required(VERSION 3.15)
project(test_cvm C)

find_package(cvm REQUIRED CONFIG)

add_executable(cvm_consumer test_consumer.c)
target_link_libraries(cvm_consumer PRIVATE cvm::v2client)

add_executable(cvm_marker_helper marker_helper.c)

add_executable(cvm_pipe_failure test_pipe_failure.c)
target_link_libraries(cvm_pipe_failure PRIVATE cvm::v2client)
