cmake_minimum_required(VERSION 3.15)
project(test_libarchive C)

find_package(libarchive REQUIRED)

add_executable(test_libarchive test.c)
target_link_libraries(test_libarchive LibArchive::LibArchive)

enable_testing()
add_test(NAME test_libarchive COMMAND test_libarchive)
