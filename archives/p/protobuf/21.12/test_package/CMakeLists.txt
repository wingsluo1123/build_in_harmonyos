cmake_minimum_required(VERSION 3.15)
project(test_protobuf CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(protobuf REQUIRED)

# person.pb.cc / person.pb.h 由 protoc 预生成（OHOS 中 Conan cache 的 protoc 未签名无法执行）
add_executable(test_protobuf test_protobuf.cpp person.pb.cc)
target_link_libraries(test_protobuf protobuf::protobuf)
target_include_directories(test_protobuf PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

enable_testing()
add_test(NAME test_protobuf COMMAND test_protobuf)
