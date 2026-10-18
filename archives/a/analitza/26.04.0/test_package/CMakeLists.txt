cmake_minimum_required(VERSION 3.16)
project(test_analitza LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Analitza6Config.cmake runs find_dependency(Qt6Core) and
# find_dependency(Qt6Xml); the exported KF6::AnalitzaWidgets target carries
# Qt::Widgets in its interface. The package installs its own config
# (cmake_find_mode=none), so this resolves against the real
# Analitza6Targets.cmake with the KF6:: namespace.
find_package(Qt6 6.5.2 REQUIRED COMPONENTS Core Gui Widgets Xml)
find_package(Analitza6 REQUIRED)

# Consumer executor: expression engine, 2D/3D plot pipeline, the X3D export
# path, the Gui models and the Widgets views.
add_executable(test_analitza test.cpp)
target_link_libraries(test_analitza PRIVATE
    KF6::Analitza
    KF6::AnalitzaPlot
    KF6::AnalitzaGui
    KF6::AnalitzaWidgets
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets)

# OHOS ELF regression check: the packaged library's DT_SONAME/DT_NEEDED
# entries and the consumer executable's own dynamic section.
add_executable(test_ohos_soname test_ohos_soname.cpp)
target_link_libraries(test_ohos_soname PRIVATE
    KF6::Analitza
    KF6::AnalitzaPlot
    Qt6::Core
    Qt6::Gui)
