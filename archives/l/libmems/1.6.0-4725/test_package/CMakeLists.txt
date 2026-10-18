cmake_minimum_required(VERSION 3.15)
project(test_libmems C)

find_package(libmems REQUIRED)

add_executable(test_mems test_mems.c)
target_link_libraries(test_mems libmems::libmems)

enable_testing()
add_test(NAME test_mems COMMAND test_mems)
