cmake_minimum_required(VERSION 3.15)
project(test_opencore-amr C CXX)

find_package(opencore-amr REQUIRED)

add_executable(test_opencore-amr test.c)
target_link_libraries(test_opencore-amr opencore-amr::opencore-amrnb opencore-amr::opencore-amrwb)

enable_testing()
add_test(NAME test_opencore-amr COMMAND test_opencore-amr)
