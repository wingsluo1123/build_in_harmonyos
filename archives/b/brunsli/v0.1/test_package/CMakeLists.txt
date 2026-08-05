cmake_minimum_required(VERSION 3.15)
project(test_brunsli CXX)

find_package(brunsli REQUIRED)

add_executable(test_brunsli test.cpp)
target_link_libraries(test_brunsli brunsli::brunsli)

enable_testing()
add_test(NAME test_brunsli COMMAND test_brunsli)
