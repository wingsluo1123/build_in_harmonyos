cmake_minimum_required(VERSION 3.16)
project(test_ktextwidgets LANGUAGES CXX)

find_package(Qt6 CONFIG REQUIRED COMPONENTS Widgets)
find_package(KF6TextWidgets CONFIG REQUIRED)

add_executable(test_ktextwidgets test_ktextwidgets.cpp)
target_link_libraries(test_ktextwidgets PRIVATE Qt6::Widgets KF6::TextWidgets)

enable_testing()
add_test(NAME test_ktextwidgets COMMAND test_ktextwidgets)