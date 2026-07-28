cmake_minimum_required(VERSION 3.16)
project(test_v_metadata CXX)

add_executable(test_v_metadata test_v_metadata.cpp)
target_compile_features(test_v_metadata PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_v_metadata COMMAND test_v_metadata)
