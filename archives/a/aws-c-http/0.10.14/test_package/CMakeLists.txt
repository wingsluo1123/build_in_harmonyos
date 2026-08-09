cmake_minimum_required(VERSION 3.15)
project(test_aws-c-http C)

find_package(aws-c-http REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-cal REQUIRED)

add_executable(test_aws-c-http test.c)
target_link_libraries(test_aws-c-http
    aws-c-http::aws-c-http
    aws-c-common::aws-c-common
    aws-c-io::aws-c-io
    aws-c-cal::aws-c-cal
)
# Workaround: cpp_info.includedirs not propagated for some packages on OHOS
foreach(pkg aws-c-common aws-c-io aws-c-cal)
    if(${pkg}_PACKAGE_FOLDER_RELEASE)
        target_include_directories(test_aws-c-http PRIVATE "${${pkg}_PACKAGE_FOLDER_RELEASE}/include")
    endif()
endforeach()

enable_testing()
add_test(NAME test_aws-c-http COMMAND test_aws-c-http)
