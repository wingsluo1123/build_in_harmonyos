cmake_minimum_required(VERSION 3.15)
project(test_kparts CXX)

# KF6Parts config chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Xml)
find_package(KF6Parts REQUIRED)

add_executable(test_kparts test.cpp)
target_link_libraries(test_kparts KF6::Parts)

enable_testing()
add_test(NAME test_kparts COMMAND test_kparts)
