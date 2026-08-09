cmake_minimum_required(VERSION 3.15)
project(test_aws-c-compression C)

find_package(aws-c-compression REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-c-compression test.c)
target_link_libraries(test_aws-c-compression
    aws-c-compression::aws-c-compression
    aws-c-common::aws-c-common
)
if(aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_aws-c-compression PRIVATE "${aws-c-common_PACKAGE_FOLDER_RELEASE}/include")
endif()

enable_testing()
add_test(NAME test_aws-c-compression COMMAND test_aws-c-compression)
