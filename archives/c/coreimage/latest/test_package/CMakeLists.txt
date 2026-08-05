cmake_minimum_required(VERSION 3.16)
project(test_coreimage CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(cprime REQUIRED)

add_executable(test_coreimage test.cpp)
target_link_libraries(test_coreimage PRIVATE cprime::cprime Qt6::Core Qt6::Gui Qt6::Widgets)

enable_testing()
add_test(NAME test_coreimage COMMAND test_coreimage)
