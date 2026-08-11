cmake_minimum_required(VERSION 3.15)
project(test_qtsvg CXX)

# Qt6Config.cmake (from qtbase) defines the _qt_internal_* helper macros
# that Qt6SvgConfig.cmake relies on, so load it first.
find_package(Qt6 REQUIRED)
find_package(Qt6Svg REQUIRED)

# test.cpp exercises the Qt6Svg core API (QSvgRenderer) only; Qt6::SvgWidgets
# is not referenced, so it is not linked here (R34: link what you call).
add_executable(test_qtsvg test.cpp)
target_link_libraries(test_qtsvg Qt6::Svg)

enable_testing()
add_test(NAME test_qtsvg COMMAND test_qtsvg)
