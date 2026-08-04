cmake_minimum_required(VERSION 3.15)
project(test_aws_checksums C)

find_package(aws-checksums REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(${PROJECT_NAME} test_main.c)
target_link_libraries(${PROJECT_NAME} aws-checksums::aws-checksums aws-c-common::aws-c-common)

# aws-c-common recipe doesn't expose include dirs via cpp_info, add manually
if(DEFINED aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(${PROJECT_NAME} PRIVATE ${aws-c-common_PACKAGE_FOLDER_RELEASE}/include)
endif()
