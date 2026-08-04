cmake_minimum_required(VERSION 3.15)
project(test_aws_c_auth C)

find_package(aws-c-auth REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-sdkutils REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-http REQUIRED)

add_executable(test_aws-c-auth test.c)
target_link_libraries(test_aws-c-auth
    aws-c-auth::aws-c-auth
    aws-c-common::aws-c-common
    aws-c-cal::aws-c-cal
    aws-c-sdkutils::aws-c-sdkutils
    aws-c-io::aws-c-io
    aws-c-http::aws-c-http
)
