cmake_minimum_required(VERSION 3.15)
project(test_falcosecurity_libs C)

find_package(falcosecurity-libs REQUIRED CONFIG)

add_executable(test_falcosecurity_libs test_falcosecurity_libs.c)
target_link_libraries(test_falcosecurity_libs PRIVATE falcosecurity-libs::falcosecurity-libs)
