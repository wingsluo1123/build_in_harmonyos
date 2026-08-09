cmake_minimum_required(VERSION 3.15)
project(test_aws-c-s3 C)

find_package(aws-c-s3 REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-auth REQUIRED)
find_package(aws-checksums REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-sdkutils REQUIRED)
find_package(aws-c-compression REQUIRED)
find_package(aws-c-event-stream REQUIRED)

add_executable(test_aws-c-s3 test.c)
target_link_libraries(test_aws-c-s3
    aws-c-s3::aws-c-s3
    aws-c-common::aws-c-common
    aws-c-io::aws-c-io
    aws-c-auth::aws-c-auth
    aws-checksums::aws-checksums
    aws-c-http::aws-c-http
    aws-c-cal::aws-c-cal
    aws-c-sdkutils::aws-c-sdkutils
    aws-c-compression::aws-c-compression
    aws-c-event-stream::aws-c-event-stream
)
# Workaround: cpp_info.includedirs not propagated for some packages on OHOS
foreach(pkg aws-c-common aws-c-io aws-c-auth aws-c-cal aws-c-sdkutils aws-c-compression aws-c-event-stream aws-checksums aws-c-http)
    if(${pkg}_PACKAGE_FOLDER_RELEASE)
        target_include_directories(test_aws-c-s3 PRIVATE "${${pkg}_PACKAGE_FOLDER_RELEASE}/include")
    endif()
endforeach()

enable_testing()
add_test(NAME test_aws-c-s3 COMMAND test_aws-c-s3)
