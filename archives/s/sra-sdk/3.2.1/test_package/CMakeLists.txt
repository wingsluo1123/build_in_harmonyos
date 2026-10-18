cmake_minimum_required(VERSION 3.16)
project(sra-sdk-test-package CXX)

find_package(sra-sdk CONFIG REQUIRED)

add_executable(test-ngs-api test_ngs.cpp)
target_link_libraries(test-ngs-api PRIVATE sra-sdk::sra-sdk)
set_target_properties(test-ngs-api PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)
