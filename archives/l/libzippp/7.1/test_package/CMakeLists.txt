cmake_minimum_required(VERSION 3.15)
project(test_libzippp CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libzippp REQUIRED)

add_executable(test_libzippp test.cpp)
target_link_libraries(test_libzippp libzippp::libzippp)

enable_testing()
add_test(NAME test_libzippp COMMAND test_libzippp)
