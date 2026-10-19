cmake_minimum_required(VERSION 3.19)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# FutureSQL6Config.cmake installs the FutureSQL6::FutureSQL target and pulls in
# Qt6Core/Qt6Sql through find_dependency.
find_package(FutureSQL6 REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE FutureSQL6::FutureSQL)
