cmake_minimum_required(VERSION 3.16)
project(test_kdoctools CXX)

# R34: 实质调用 KF6::DocTools API
find_package(KF6DocTools REQUIRED CONFIG)

add_executable(test_kdoctools src/test_kdoctools.cpp)
target_link_libraries(test_kdoctools PRIVATE KF6::DocTools)

enable_testing()
add_test(NAME kdoctools_link COMMAND test_kdoctools)
