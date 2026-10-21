cmake_minimum_required(VERSION 3.16)
project(test_kywc C)

find_package(PkgConfig REQUIRED)

# Use the minimal wayland-client.pc written by the test_package recipe: the
# PkgConfigDeps aggregate also lists libwayland-cursor/libwayland-egl, whose
# ELFs the OHOS loader rejects (plasma-wayland-protocols precedent).
if(WAYLAND_CLIENT_PC_DIR)
    set(ENV{PKG_CONFIG_PATH} "${WAYLAND_CLIENT_PC_DIR}:$ENV{PKG_CONFIG_PATH}")
endif()

# Same discovery path as ukui-quick 4.22.0.1 window-thumbnail:
# pkg_check_modules(... REQUIRED kywc), headers via #include <libkywc.h>.
pkg_check_modules(KYWC REQUIRED IMPORTED_TARGET kywc)
pkg_check_modules(WAYLAND_CLIENT REQUIRED IMPORTED_TARGET wayland-client)

# libwayland-server is taken by explicit path rather than as part of an
# aggregate wayland target: the published wayland package also ships
# libwayland-cursor.so / libwayland-egl.so, which the OHOS loader rejects, and
# linking them would make this binary fail to start
# (plasma-wayland-protocols precedent).
find_library(WAYLAND_SERVER_LIB NAMES wayland-server
             PATHS ${WAYLAND_CLIENT_LIBRARY_DIRS} NO_DEFAULT_PATH)
if(NOT WAYLAND_SERVER_LIB)
    message(FATAL_ERROR
            "libwayland-server not found under ${WAYLAND_CLIENT_LIBRARY_DIRS}")
endif()

find_package(Threads REQUIRED)

add_executable(test_kywc test_kywc.c)
target_link_libraries(test_kywc PRIVATE
    PkgConfig::KYWC
    PkgConfig::WAYLAND_CLIENT
    ${WAYLAND_SERVER_LIB}
    Threads::Threads)
