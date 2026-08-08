cmake_minimum_required(VERSION 3.15)
project(test_apr_util C)

find_package(apr REQUIRED)
find_package(apr-util REQUIRED)
find_package(expat REQUIRED)

add_executable(test_apr_util test.c)
target_link_libraries(test_apr_util apr-util::apr-util apr::apr expat::expat)

enable_testing()
add_test(NAME test_apr_util COMMAND test_apr_util)
