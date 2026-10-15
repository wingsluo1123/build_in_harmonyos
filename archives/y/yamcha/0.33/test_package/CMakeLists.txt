cmake_minimum_required(VERSION 3.15)
project(yamcha_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(yamcha CONFIG REQUIRED)

add_executable(yamcha_api_test test_yamcha.cpp)
target_link_libraries(yamcha_api_test PRIVATE yamcha::yamcha)
