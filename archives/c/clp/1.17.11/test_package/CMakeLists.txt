cmake_minimum_required(VERSION 3.15)
project(clp_test LANGUAGES CXX)

find_package(clp REQUIRED)

add_executable(test_clp test.cpp)
target_link_libraries(test_clp PRIVATE clp::clp pthread)

enable_testing()
add_test(NAME test_clp COMMAND test_clp)
