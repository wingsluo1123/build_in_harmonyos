cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# grpc and protobuf ship cmake_find_mode=none, so CMakeDeps does not generate
# configs for them. Locate the real registry configs first (the *_DIR
# variables are pinned by the test conanfile), bridge the lowercase target
# names the generated config expects, and pre-set the *_FOUND variables so the
# dependency loop in the generated config skips its find_dependency calls.
find_package(gRPC CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)

if(NOT TARGET grpc::grpc)
  add_library(grpc::grpc INTERFACE IMPORTED)
  set_target_properties(grpc::grpc PROPERTIES
                        INTERFACE_LINK_LIBRARIES "gRPC::grpc++;gRPC::grpc;gRPC::gpr")
endif()
if(NOT TARGET protobuf::protobuf)
  add_library(protobuf::protobuf INTERFACE IMPORTED)
  set_target_properties(protobuf::protobuf PROPERTIES
                        INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
endif()
set(grpc_FOUND TRUE)
set(protobuf_FOUND TRUE)

find_package(libkysdk-vector-engine-client CONFIG REQUIRED)

add_executable(test_vector_client test_vector_client.cpp)
target_link_libraries(test_vector_client PRIVATE
                      libkysdk-vector-engine-client::libkysdk-vector-engine-client)

enable_testing()
add_test(NAME vector_client_smoke COMMAND test_vector_client)
