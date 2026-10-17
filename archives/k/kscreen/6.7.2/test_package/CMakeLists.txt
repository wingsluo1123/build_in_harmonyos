cmake_minimum_required(VERSION 3.16)
project(test_kscreen_plugin CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# QPluginLoader/QProcess/QJsonObject live in QtCore; the plugin's own KF6
# dependencies are resolved at runtime through the recorded package
# lib/ directories (LD_LIBRARY_PATH set by the test driver).
find_package(Qt6 REQUIRED COMPONENTS Core)

add_executable(test_kscreen_plugin test_kscreen_plugin.cpp)
target_link_libraries(test_kscreen_plugin Qt6::Core)

enable_testing()
add_test(NAME test_kscreen_plugin COMMAND test_kscreen_plugin)
