cmake_minimum_required(VERSION 3.15)
project(test_kglobalaccel CXX)

# KF6GlobalAccelTargets.cmake references Qt6::DBus/Qt6::Widgets targets, so
# load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(KF6GlobalAccel REQUIRED)

add_executable(test_kglobalaccel test.cpp)
target_link_libraries(test_kglobalaccel KF6::GlobalAccel Qt6::Widgets)
