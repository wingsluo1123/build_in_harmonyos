cmake_minimum_required(VERSION 3.15)
project(test_cpr CXX)

find_package(cpr REQUIRED)

add_executable(test_cpr test_cpr.cpp)
target_link_libraries(test_cpr cpr::cpr)

enable_testing()
add_test(NAME test_cpr COMMAND test_cpr)