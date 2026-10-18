cmake_minimum_required(VERSION 3.15)
project(test_cascade_compiler LANGUAGES CXX)

find_package(CascadeCompiler CONFIG REQUIRED)

add_executable(test_cascade test_cascade.cpp)
target_compile_features(test_cascade PRIVATE cxx_std_17)
target_link_libraries(test_cascade PRIVATE CascadeCompiler::Cascade)
