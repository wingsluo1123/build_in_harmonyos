# QCustomPlot 2.1.1 — OHOS build wrapper.
#
# Upstream publishes only qcustomplot.cpp / qcustomplot.h (no build system).
# This file builds the shared or static library, installs the public header and
# exports a relocatable CMake package (QCustomPlotConfig.cmake, target
# QCustomPlot::QCustomPlot) that consumers can use directly.
cmake_minimum_required(VERSION 3.21)

# The version comes from conan_toolchain.cmake, which CMake loads inside the
# first project() call: QCUSTOMPLOT_VERSION is not defined while the
# project() arguments are expanded, so the version is applied afterwards.
project(QCustomPlot LANGUAGES CXX)

if(NOT QCUSTOMPLOT_VERSION)
  message(FATAL_ERROR "QCUSTOMPLOT_VERSION is not set (expected from conan_toolchain.cmake)")
endif()
string(REGEX MATCH "^[0-9]+" QCUSTOMPLOT_SOVERSION "${QCUSTOMPLOT_VERSION}")

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# QtPrintSupport capability probe. OHOS qtbase is built with
# FEATURE_printsupport=OFF and ships no Qt6PrintSupport module; the module is
# optional here and the compile definition below mirrors the upstream
# QT_NO_PRINTER code path (qcustomplot.cpp already guards savePdf with it).
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(Qt6 QUIET OPTIONAL_COMPONENTS PrintSupport)

add_library(QCustomPlot
  ${CMAKE_CURRENT_SOURCE_DIR}/qcustomplot.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/qcustomplot.h
)
add_library(QCustomPlot::QCustomPlot ALIAS QCustomPlot)

target_compile_features(QCustomPlot PUBLIC cxx_std_17)
target_include_directories(QCustomPlot PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_link_libraries(QCustomPlot PUBLIC Qt6::Core Qt6::Gui Qt6::Widgets)

set(QCUSTOMPLOT_WITH_PRINTSUPPORT OFF)
if(Qt6PrintSupport_FOUND AND TARGET Qt6::PrintSupport)
  set(QCUSTOMPLOT_WITH_PRINTSUPPORT ON)
  target_link_libraries(QCustomPlot PUBLIC Qt6::PrintSupport)
else()
  message(STATUS "Qt6PrintSupport not available: savePdf uses the QT_NO_PRINTER stub")
  target_compile_definitions(QCustomPlot PUBLIC QT_NO_PRINTER)
endif()

if(BUILD_SHARED_LIBS)
  target_compile_definitions(QCustomPlot PRIVATE QCUSTOMPLOT_COMPILE_LIBRARY)
  target_compile_definitions(QCustomPlot INTERFACE QCUSTOMPLOT_USE_LIBRARY)
endif()

set_target_properties(QCustomPlot PROPERTIES
  EXPORT_NAME QCustomPlot
  OUTPUT_NAME QCustomPlot
  VERSION ${QCUSTOMPLOT_VERSION}
  SOVERSION ${QCUSTOMPLOT_SOVERSION}
)

install(TARGETS QCustomPlot EXPORT QCustomPlotTargets
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/qcustomplot.h
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

set(QCUSTOMPLOT_CONFIG_INSTALL_DIR ${CMAKE_INSTALL_LIBDIR}/cmake/QCustomPlot)

install(EXPORT QCustomPlotTargets
  FILE QCustomPlotTargets.cmake
  NAMESPACE QCustomPlot::
  DESTINATION ${QCUSTOMPLOT_CONFIG_INSTALL_DIR}
)

configure_package_config_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake/QCustomPlotConfig.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/QCustomPlotConfig.cmake
  INSTALL_DESTINATION ${QCUSTOMPLOT_CONFIG_INSTALL_DIR}
)
write_basic_package_version_file(
  ${CMAKE_CURRENT_BINARY_DIR}/QCustomPlotConfigVersion.cmake
  VERSION ${QCUSTOMPLOT_VERSION}
  COMPATIBILITY SameMajorVersion
)
install(FILES
  ${CMAKE_CURRENT_BINARY_DIR}/QCustomPlotConfig.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/QCustomPlotConfigVersion.cmake
  DESTINATION ${QCUSTOMPLOT_CONFIG_INSTALL_DIR}
)
