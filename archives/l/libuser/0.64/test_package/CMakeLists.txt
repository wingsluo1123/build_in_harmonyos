cmake_minimum_required(VERSION 3.15)
project(test_libuser C)

find_package(libuser CONFIG REQUIRED)

add_executable(test_libuser test_libuser.c)
target_link_libraries(test_libuser PRIVATE libuser::libuser)

enable_testing()
add_test(NAME test_libuser COMMAND test_libuser)
