cmake_minimum_required(VERSION 3.15)
project(test_aws-c-cal C)

find_package(aws-c-cal REQUIRED)

add_executable(test_aws-c-cal test.c)
target_link_libraries(test_aws-c-cal AWS::aws-c-cal)

enable_testing()
add_test(NAME test_aws-c-cal COMMAND test_aws-c-cal)
