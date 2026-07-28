cmake_minimum_required(VERSION 3.15)
project(test_rhash C)

find_package(Rhash REQUIRED CONFIG)

add_executable(test_rhash test_rhash.c)
target_link_libraries(test_rhash PRIVATE Rhash::Rhash)

enable_testing()
add_test(NAME rhash_test COMMAND test_rhash)
