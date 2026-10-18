cmake_minimum_required(VERSION 3.16)
project(kmines_consumer_test CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KDEGames6Config.cmake pulls Qt6Widgets/Xml/Network/Qml and
# KF6Config/ConfigWidgets/Completion in through find_dependency; every one
# of those packages is in the test graph (libkdegames requirement closure).
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KDEGames6 REQUIRED)

# The consumer test drives the installed kmines binary and exercises the
# KGameThemeProvider/KGameRenderer runtime data path the game uses at
# startup, so it links the same KDEGames6 library the game links.
add_executable(kmines_consumer_test main.cpp)
target_link_libraries(kmines_consumer_test PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    KDEGames6
)
