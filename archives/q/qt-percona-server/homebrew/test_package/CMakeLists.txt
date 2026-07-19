cmake_minimum_required(VERSION 3.16)
project(test_qt_percona_server LANGUAGES CXX)

find_package(Qt6 COMPONENTS Core Sql REQUIRED)

add_executable(test_driver test_driver.cpp)
target_link_libraries(test_driver PRIVATE Qt6::Core Qt6::Sql)

enable_testing()
add_test(NAME test_driver COMMAND test_driver)
