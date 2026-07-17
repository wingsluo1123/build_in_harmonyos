cmake_minimum_required(VERSION 3.14)
project(nanopb_test C)

enable_testing()

find_package(nanopb CONFIG REQUIRED)

add_executable(test_nanopb test.c)
target_link_libraries(test_nanopb PRIVATE nanopb::protobuf-nanopb-static)

add_test(NAME runtime_encode_decode COMMAND test_nanopb)
