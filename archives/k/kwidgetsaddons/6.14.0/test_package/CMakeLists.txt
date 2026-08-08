cmake_minimum_required(VERSION 3.16)
project(test_kwidgetsaddons CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6WidgetsAddonsTargets.cmake references
find_package(Qt6 COMPONENTS Core Widgets REQUIRED)

find_package(KF6WidgetsAddons REQUIRED NO_MODULE)

add_executable(test_kwidgetsaddons test_kwidgetsaddons.cpp)
target_link_libraries(test_kwidgetsaddons KF6::WidgetsAddons Qt6::Widgets)

enable_testing()
add_test(NAME test_kwidgetsaddons COMMAND test_kwidgetsaddons)
