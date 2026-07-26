cmake_minimum_required(VERSION 3.15)
project(test_libxcrypt C)

enable_testing()
find_package(libxcrypt CONFIG REQUIRED)

add_executable(test_libxcrypt test.c)
target_link_libraries(test_libxcrypt PRIVATE libxcrypt::libxcrypt)
add_test(NAME test_libxcrypt COMMAND test_libxcrypt)
