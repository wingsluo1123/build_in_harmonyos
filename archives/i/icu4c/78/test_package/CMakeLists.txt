cmake_minimum_required(VERSION 3.15)
project(test_icu4c CXX)

find_package(ICU REQUIRED)

add_executable(test_icu4c test.cpp)
target_link_libraries(test_icu4c icu4c::icu4c)

enable_testing()
add_test(NAME icu4c_test COMMAND test_icu4c)
