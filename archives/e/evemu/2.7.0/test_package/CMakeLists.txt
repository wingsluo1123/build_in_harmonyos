cmake_minimum_required(VERSION 3.15)
project(test_evemu C CXX)

find_package(evemu REQUIRED)

# C consumer (mirrors upstream test/test-c-compile.c)
add_executable(test_evemu test.c test_cpp.cpp)
target_link_libraries(test_evemu evemu::evemu)

enable_testing()
add_test(NAME test_evemu COMMAND test_evemu)
