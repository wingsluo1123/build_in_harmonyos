cmake_minimum_required(VERSION 3.15)
project(test_aws-checksums C)

# Find both packages explicitly via Conan CMakeDeps
find_package(aws-checksums REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws-checksums test.c)
target_link_libraries(test_aws-checksums aws-checksums::aws-checksums aws-c-common::aws-c-common)

# Workaround: aws-c-common recipe doesn't export cpp_info.includedirs,
# so INTERFACE_INCLUDE_DIRECTORIES is empty. Use PACKAGE_FOLDER as fallback.
if(DEFINED aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_aws-checksums PRIVATE
        "${aws-c-common_PACKAGE_FOLDER_RELEASE}/include")
elseif(DEFINED aws-c-common_PACKAGE_FOLDER)
    target_include_directories(test_aws-checksums PRIVATE
        "${aws-c-common_PACKAGE_FOLDER}/include")
endif()

enable_testing()
add_test(NAME test_aws-checksums COMMAND test_aws-checksums)
