cmake_minimum_required(VERSION 3.5)
project(test_libexif C)

find_package(libexif REQUIRED)

add_executable(test_libexif test_libexif.c)
target_link_libraries(test_libexif PRIVATE libexif::libexif)

enable_testing()
add_test(NAME test_libexif COMMAND test_libexif)
