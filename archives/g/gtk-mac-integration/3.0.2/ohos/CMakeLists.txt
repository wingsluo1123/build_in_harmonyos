cmake_minimum_required(VERSION 3.15)
project(gtk_mac_integration_ohos LANGUAGES C)

include(GNUInstallDirs)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0 gobject-2.0)

add_library(gtkmacintegration-gtk3 STATIC gtkosxapplication-ohos.c)
target_compile_features(gtkmacintegration-gtk3 PRIVATE c_std_11)
target_compile_definitions(
    gtkmacintegration-gtk3 PUBLIC GTKOSX_HARMONYOS_COMPAT=1
)
target_include_directories(
    gtkmacintegration-gtk3
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/gtkmacintegration>
)
target_link_libraries(gtkmacintegration-gtk3 PUBLIC PkgConfig::GLIB)

install(
    TARGETS gtkmacintegration-gtk3
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(
    FILES gtkosxapplication.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/gtkmacintegration
)
