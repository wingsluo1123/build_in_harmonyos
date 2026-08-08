cmake_minimum_required(VERSION 3.16)
project(test_solid CXX)

# qtbase uses cmake_find_mode=none, so we must find Qt6 first
# to create the Qt6:: targets that KF6SolidTargets.cmake references
find_package(Qt6 COMPONENTS Core Xml Gui REQUIRED)

find_package(KF6Solid REQUIRED NO_MODULE)

add_executable(test_solid test_solid.cpp)
target_link_libraries(test_solid KF6::Solid)

enable_testing()
add_test(NAME test_solid COMMAND test_solid)
