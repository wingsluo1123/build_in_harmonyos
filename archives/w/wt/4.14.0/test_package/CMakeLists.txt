cmake_minimum_required(VERSION 3.15)
project(test_wt CXX)

find_package(wt CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_wt test_wt.cpp)
target_link_libraries(test_wt PRIVATE wt::wt wt::wthttp Threads::Threads)
