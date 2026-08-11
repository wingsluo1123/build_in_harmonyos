cmake_minimum_required(VERSION 3.15)
project(test_qtsvg CXX)

# Qt6Config.cmake (from qtbase) defines the _qt_internal_* helper macros
# that Qt6SvgConfig.cmake relies on, so load it first.
find_package(Qt6 REQUIRED)
find_package(Qt6Svg REQUIRED)
find_package(Qt6SvgWidgets REQUIRED)

add_executable(test_qtsvg test.cpp)
target_link_libraries(test_qtsvg Qt6::Svg Qt6::SvgWidgets)

enable_testing()
add_test(NAME test_qtsvg COMMAND test_qtsvg)
