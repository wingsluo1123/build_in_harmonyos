cmake_minimum_required(VERSION 3.15)
project(test_kpty CXX)

find_package(KF6Pty REQUIRED)

add_executable(test_kpty test.cpp)
target_link_libraries(test_kpty KF6::Pty)

enable_testing()
add_test(NAME test_kpty COMMAND test_kpty)
