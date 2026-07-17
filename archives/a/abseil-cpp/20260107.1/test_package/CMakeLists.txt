cmake_minimum_required(VERSION 3.15)
project(test_abseil_cpp CXX)

find_package(absl REQUIRED)

add_executable(test_abseil_cpp test.cpp)
target_link_libraries(test_abseil_cpp abseil-cpp::abseil-cpp)

set_target_properties(test_abseil_cpp PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_abseil_cpp COMMAND test_abseil_cpp)
