cmake_minimum_required(VERSION 3.15)
project(test_libmp3splt C)

find_package(libmp3splt REQUIRED)

add_executable(test_libmp3splt test.c)
target_link_libraries(test_libmp3splt libmp3splt::libmp3splt)

enable_testing()
add_test(NAME test_libmp3splt COMMAND test_libmp3splt)
