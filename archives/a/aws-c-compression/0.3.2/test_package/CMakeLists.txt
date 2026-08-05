cmake_minimum_required(VERSION 3.15)
project(test_aws-c-compression C)

# Find the package via Conan-generated CMakeDeps
find_package(aws-c-compression REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-c-compression test.c)

# CMakeDeps may not propagate include dirs for aws-c-common on OHOS,
# so add them manually using the package folder variable
if(DEFINED aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_aws-c-compression PRIVATE ${aws-c-common_PACKAGE_FOLDER_RELEASE}/include)
endif()

target_link_libraries(test_aws-c-compression aws-c-compression::aws-c-compression aws-c-common::aws-c-common)

enable_testing()
add_test(NAME test_aws-c-compression COMMAND test_aws-c-compression)
