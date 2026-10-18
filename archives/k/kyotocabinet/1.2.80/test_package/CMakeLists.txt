cmake_minimum_required(VERSION 3.15)
project(test_kyotocabinet CXX)

find_package(kyotocabinet REQUIRED)

add_executable(test_kyotocabinet test.cpp)
target_link_libraries(test_kyotocabinet PRIVATE kyotocabinet::kyotocabinet)

# C++11 required (KC headers use std::unordered_map etc.)
target_compile_features(test_kyotocabinet PRIVATE cxx_std_11)
set_target_properties(test_kyotocabinet PROPERTIES CXX_STANDARD 11)
