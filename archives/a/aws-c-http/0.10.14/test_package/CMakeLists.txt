cmake_minimum_required(VERSION 3.15)
project(test_aws-c-http C)

find_package(aws-c-http REQUIRED)

add_executable(test_aws-c-http test.c)
target_link_libraries(test_aws-c-http AWS::aws-c-http)

enable_testing()
add_test(NAME test_aws-c-http COMMAND test_aws-c-http)
