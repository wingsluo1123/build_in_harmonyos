cmake_minimum_required(VERSION 3.15)
project(test_libaccounts_qt CXX)

find_package(libaccounts-qt REQUIRED)

add_executable(test_libaccounts_qt test.cpp)
target_link_libraries(test_libaccounts_qt libaccounts-qt::libaccounts-qt)

enable_testing()
add_test(NAME test_libaccounts_qt COMMAND test_libaccounts_qt)
