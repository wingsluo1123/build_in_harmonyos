cmake_minimum_required(VERSION 3.15)
project(test_aws-c-event-stream C)

find_package(aws-c-event-stream REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-c-event-stream test.c)
target_link_libraries(test_aws-c-event-stream aws-c-event-stream::aws-c-event-stream aws-c-common::aws-c-common)

enable_testing()
add_test(NAME test_aws-c-event-stream COMMAND test_aws-c-event-stream)
