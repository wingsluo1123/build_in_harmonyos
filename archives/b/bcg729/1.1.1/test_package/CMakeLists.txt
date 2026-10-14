cmake_minimum_required(VERSION 3.15)
project(test_bcg729 C)

find_package(bcg729 REQUIRED)

add_executable(test_bcg729 test.c)
target_link_libraries(test_bcg729 bcg729::bcg729)

enable_testing()
add_test(NAME test_bcg729 COMMAND test_bcg729)
