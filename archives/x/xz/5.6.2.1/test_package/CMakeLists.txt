cmake_minimum_required(VERSION 3.15)
project(test_package C)

include(CTest)
find_package(xz CONFIG REQUIRED)

add_executable(test_xz test_xz.c)
target_link_libraries(test_xz PRIVATE xz::xz)
add_test(NAME static_liblzma_round_trip COMMAND test_xz)
