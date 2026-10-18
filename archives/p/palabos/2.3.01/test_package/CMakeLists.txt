cmake_minimum_required(VERSION 3.15)
project(test_palabos CXX)

find_package(palabos REQUIRED)

add_executable(test_palabos test_palabos.cpp)
target_link_libraries(test_palabos palabos::palabos)

enable_testing()
add_test(NAME test_palabos COMMAND test_palabos)
