cmake_minimum_required(VERSION 3.16)
project(test_qt_advanced_docking_system LANGUAGES CXX)

# Qt6 first: qtbase ships its own Qt6Config.cmake (cmake_find_mode=none), which
# conanfile.py puts on CMAKE_PREFIX_PATH. Finding it up front also short-circuits
# the find_dependency(Qt6) that the package config performs.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)

# The packaged target: find_package(qtadvanceddocking-qt6) + ads::qtadvanceddocking-qt6
# mirrors the upstream install tree (CMakeDeps generates the config).
find_package(qtadvanceddocking-qt6 REQUIRED)

add_executable(test_qt_advanced_docking_system test_qt_advanced_docking_system.cpp)

set_target_properties(test_qt_advanced_docking_system PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

target_link_libraries(test_qt_advanced_docking_system PRIVATE
    ads::qtadvanceddocking-qt6
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
)
