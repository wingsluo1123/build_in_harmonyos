cmake_minimum_required(VERSION 3.16)
project(xsettings_test C)

find_package(xsettings REQUIRED CONFIG)

add_executable(test_xsettings_consumer test_xsettings.c)
target_link_libraries(test_xsettings_consumer PRIVATE xsettings::xsettings)
