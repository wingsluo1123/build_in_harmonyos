cmake_minimum_required(VERSION 3.15)
project(test_ksyntaxhighlighting5 CXX)

set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

find_package(Qt5 REQUIRED COMPONENTS Core Gui)
find_package(KF5SyntaxHighlighting REQUIRED)

add_executable(test_ksyntaxhighlighting5 test.cpp)
target_link_libraries(test_ksyntaxhighlighting5 KF5::SyntaxHighlighting Qt5::Core Qt5::Gui)
