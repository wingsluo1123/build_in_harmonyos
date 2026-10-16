cmake_minimum_required(VERSION 3.16)
project(test_kcron LANGUAGES CXX)

if(NOT DEFINED KCRON_PACKAGE_DIR)
    message(FATAL_ERROR "KCRON_PACKAGE_DIR not set (see test_package/conanfile.py generate())")
endif()

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Widgets)
find_package(KF6KCMUtils REQUIRED CONFIG)
find_package(KF6CoreAddons REQUIRED CONFIG)

add_executable(test_kcron test_kcron.cpp)
target_link_libraries(test_kcron PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Widgets
    KF6::KCMUtilsCore
    KF6::CoreAddons
)

enable_testing()
add_test(NAME test_kcron COMMAND test_kcron "${KCRON_PACKAGE_DIR}")
