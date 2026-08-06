cmake_minimum_required(VERSION 3.15)
project(test_libsodium C)

find_package(libsodium REQUIRED)

add_executable(test_libsodium test_libsodium.c)
target_link_libraries(test_libsodium PRIVATE libsodium::libsodium)

enable_testing()
add_test(NAME libsodium_test COMMAND test_libsodium)
