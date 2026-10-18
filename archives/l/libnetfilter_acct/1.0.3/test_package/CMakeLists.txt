cmake_minimum_required(VERSION 3.15)
project(test_libnetfilter_acct C)

find_package(libnetfilter_acct REQUIRED)

add_executable(test_libnetfilter_acct test.c)
target_link_libraries(test_libnetfilter_acct libnetfilter_acct::libnetfilter_acct)

enable_testing()
add_test(NAME test_libnetfilter_acct COMMAND test_libnetfilter_acct)
