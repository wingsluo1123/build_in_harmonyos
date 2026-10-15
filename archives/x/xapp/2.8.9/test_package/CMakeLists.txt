cmake_minimum_required(VERSION 3.15)
project(test_xapp C)

find_package(PkgConfig REQUIRED)

# Assertion 1 (build-time): the xapp.pc metadata must fully resolve — name,
# version, the Requires chain (gtk+-3.0 / gobject-2.0 / cairo) and the
# Requires.private member (xkbfile). REQUIRED turns any resolution gap into a
# hard configure failure (this toolchain's pkg-config 0.29.2 resolves
# Requires(.private) members strictly even for non-static queries).
pkg_check_modules(XAPP REQUIRED IMPORTED_TARGET xapp)

# Explicit link closure for the direct gtk/gobject/gio calls in test_xapp.c —
# no implicit DT_NEEDED-closure resolution (implement-policy §5).
pkg_check_modules(GTK3 REQUIRED IMPORTED_TARGET gtk+-3.0)
pkg_check_modules(GOBJECT REQUIRED IMPORTED_TARGET gobject-2.0)
pkg_check_modules(GIO REQUIRED IMPORTED_TARGET gio-2.0)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0)

if(XAPP_VERSION VERSION_LESS "2.8.9")
    message(FATAL_ERROR "xapp.pc version mismatch: ${XAPP_VERSION} < 2.8.9")
endif()

message(STATUS "xapp.pc OK: version=${XAPP_VERSION} prefix=${XAPP_PREFIX} "
               "(Requires + Requires.private closure resolved)")

add_executable(test_xapp test_xapp.c)
target_link_libraries(test_xapp PRIVATE
    PkgConfig::XAPP
    PkgConfig::GTK3
    PkgConfig::GOBJECT
    PkgConfig::GIO
    PkgConfig::GLIB)
