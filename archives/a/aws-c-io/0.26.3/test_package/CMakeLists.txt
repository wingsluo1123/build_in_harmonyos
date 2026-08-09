cmake_minimum_required(VERSION 3.15)
project(test_aws-c-io C)

find_package(aws-c-io REQUIRED)

add_executable(test_aws-c-io test.c)
target_link_libraries(test_aws-c-io AWS::aws-c-io)

enable_testing()
add_test(NAME test_aws-c-io COMMAND test_aws-c-io)
