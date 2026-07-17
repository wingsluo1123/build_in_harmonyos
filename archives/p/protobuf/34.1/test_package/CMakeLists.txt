cmake_minimum_required(VERSION 3.15)
project(test_protobuf CXX)

find_package(protobuf REQUIRED)

add_executable(test_protobuf test.cpp)
target_link_libraries(test_protobuf protobuf::protobuf)

set_target_properties(test_protobuf PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_protobuf COMMAND test_protobuf)
