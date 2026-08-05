cmake_minimum_required(VERSION 3.15)
project(test_aws-c-mqtt C)

find_package(aws-c-mqtt REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-compression REQUIRED)

add_executable(test_aws-c-mqtt test.c)
target_link_libraries(test_aws-c-mqtt
    aws-c-mqtt::aws-c-mqtt
    aws-c-common::aws-c-common
    aws-c-http::aws-c-http
    aws-c-io::aws-c-io
    aws-c-cal::aws-c-cal
    aws-c-compression::aws-c-compression
)

enable_testing()
add_test(NAME test_aws-c-mqtt COMMAND test_aws-c-mqtt)
