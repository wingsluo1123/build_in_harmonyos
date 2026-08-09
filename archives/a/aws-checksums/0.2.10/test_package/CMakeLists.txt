cmake_minimum_required(VERSION 3.15)
project(test_aws-checksums C)

find_package(aws-checksums REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-checksums test.c)
target_link_libraries(test_aws-checksums
    aws-checksums::aws-checksums
    aws-c-common::aws-c-common
)
# Workaround: aws-c-common binary doesn't auto-detect includedirs on OHOS
if(aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_aws-checksums PRIVATE "${aws-c-common_PACKAGE_FOLDER_RELEASE}/include")
endif()

enable_testing()
add_test(NAME test_aws-checksums COMMAND test_aws-checksums)
