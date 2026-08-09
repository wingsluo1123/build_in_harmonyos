cmake_minimum_required(VERSION 3.15)
project(test_libkeyfinder)

find_package(KeyFinder REQUIRED)

add_executable(${PROJECT_NAME} test.cpp)
target_link_libraries(${PROJECT_NAME} KeyFinder::keyfinder)

enable_testing()
add_test(NAME ${PROJECT_NAME} COMMAND ${PROJECT_NAME})
