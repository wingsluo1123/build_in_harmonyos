cmake_minimum_required(VERSION 3.16)
project(test_kjobwidgets CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6JobWidgetsTargets.cmake references
find_package(Qt6 COMPONENTS Core Widgets REQUIRED)

find_package(KF6CoreAddons REQUIRED NO_MODULE)
find_package(KF6WidgetsAddons REQUIRED NO_MODULE)
find_package(KF6JobWidgets REQUIRED NO_MODULE)

add_executable(test_kjobwidgets test_kjobwidgets.cpp)
target_link_libraries(test_kjobwidgets KF6::JobWidgets)

enable_testing()
add_test(NAME test_kjobwidgets COMMAND test_kjobwidgets)
