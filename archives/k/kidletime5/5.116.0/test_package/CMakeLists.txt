cmake_minimum_required(VERSION 3.15)
project(test_kidletime5 CXX)

find_package(Qt5 CONFIG REQUIRED Core)
find_package(KF5IdleTime CONFIG REQUIRED)

add_executable(test_kidletime5 test.cpp)
target_link_libraries(test_kidletime5 KF5::IdleTime Qt5::Core)

enable_testing()
add_test(NAME test_kidletime5 COMMAND test_kidletime5)
