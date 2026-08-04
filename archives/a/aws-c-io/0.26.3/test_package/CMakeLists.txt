cmake_minimum_required(VERSION 3.15)
project(test_aws-c-io C)

find_package(aws-c-io REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-c-io test.c)
target_link_libraries(test_aws-c-io aws-c-io::aws-c-io aws-c-common::aws-c-common)

enable_testing()
add_test(NAME test_aws-c-io COMMAND test_aws-c-io)
