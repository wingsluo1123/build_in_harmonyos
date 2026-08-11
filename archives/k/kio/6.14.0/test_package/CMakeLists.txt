cmake_minimum_required(VERSION 3.15)
project(test_kio CXX)

# KF6KIO config chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network Xml Concurrent)
find_package(KF6KIO REQUIRED)

add_executable(test_kio test.cpp)
target_link_libraries(test_kio KF6::KIOCore)

enable_testing()
add_test(NAME test_kio COMMAND test_kio)
