cmake_minimum_required(VERSION 3.15)
project(papi_test C)

find_package(papi CONFIG REQUIRED)

add_executable(test_papi test_papi.c)
target_link_libraries(test_papi papi::papi)
