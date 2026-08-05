cmake_minimum_required(VERSION 3.15)
project(test_aws-c-compression C)

find_package(aws-c-compression REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-c-compression test.c)
target_link_libraries(test_aws-c-compression
    aws-c-compression::aws-c-compression
    aws-c-common::aws-c-common
)

enable_testing()
add_test(NAME test_aws-c-compression COMMAND test_aws-c-compression)
