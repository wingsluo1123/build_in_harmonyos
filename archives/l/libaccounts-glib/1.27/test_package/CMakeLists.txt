cmake_minimum_required(VERSION 3.15)
project(test_libaccounts_glib C)

find_package(libaccounts-glib REQUIRED)

add_executable(test_libaccounts_glib test.c)
target_link_libraries(test_libaccounts_glib libaccounts-glib::libaccounts-glib)

enable_testing()
add_test(NAME test_libaccounts_glib COMMAND test_libaccounts_glib)
