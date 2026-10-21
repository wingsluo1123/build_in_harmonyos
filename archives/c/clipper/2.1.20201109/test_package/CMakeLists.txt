cmake_minimum_required(VERSION 3.15)
project(test_clipper CXX)

find_package(Clipper REQUIRED CONFIG)

add_executable(test_clipper test_clipper.cpp)
target_link_libraries(test_clipper PRIVATE Clipper::clipper-core)

enable_testing()
add_test(NAME test_clipper COMMAND test_clipper)
