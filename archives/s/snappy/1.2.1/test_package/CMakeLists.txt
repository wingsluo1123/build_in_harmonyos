cmake_minimum_required(VERSION 3.15)
project(test_snappy LANGUAGES CXX)

find_package(snappy CONFIG REQUIRED)

add_executable(test_snappy test_snappy.cpp)
target_compile_features(test_snappy PRIVATE cxx_std_11)
target_link_libraries(test_snappy PRIVATE snappy::snappy)

enable_testing()
add_test(NAME test_snappy COMMAND test_snappy)
