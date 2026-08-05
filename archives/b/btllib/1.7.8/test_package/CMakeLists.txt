cmake_minimum_required(VERSION 3.15)
project(test_btllib CXX)

find_package(btllib REQUIRED CONFIG)

add_executable(test_btllib test_btllib.cpp)
target_link_libraries(test_btllib btllib::btllib)
target_compile_features(test_btllib PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_btllib COMMAND test_btllib)
