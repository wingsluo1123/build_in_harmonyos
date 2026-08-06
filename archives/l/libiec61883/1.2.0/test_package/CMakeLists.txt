cmake_minimum_required(VERSION 3.15)
project(test_libiec61883 C)

find_package(libiec61883 REQUIRED CONFIG)

add_executable(test_libiec61883 test_libiec61883.c)
target_link_libraries(test_libiec61883 PRIVATE libiec61883::libiec61883)

enable_testing()
add_test(NAME test_libiec61883 COMMAND test_libiec61883)
