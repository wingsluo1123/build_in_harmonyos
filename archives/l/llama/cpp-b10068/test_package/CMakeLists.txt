cmake_minimum_required(VERSION 3.15)
project(test_llama CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(llama CONFIG REQUIRED)

add_executable(test_llama test_llama.cpp)
target_link_libraries(test_llama PRIVATE llama::llama)
