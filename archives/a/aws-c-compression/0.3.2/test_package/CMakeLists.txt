cmake_minimum_required(VERSION 3.15)
project(test_aws-c-compression C)

find_package(aws-c-compression REQUIRED)

add_executable(test_aws-c-compression test.c)
target_link_libraries(test_aws-c-compression AWS::aws-c-compression)

enable_testing()
add_test(NAME test_aws-c-compression COMMAND test_aws-c-compression)
