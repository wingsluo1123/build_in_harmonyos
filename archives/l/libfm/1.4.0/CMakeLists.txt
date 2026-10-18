cmake_minimum_required(VERSION 3.16)
project(libfm VERSION 1.4.0 LANGUAGES C)

# GLIB path from conan — override with -DGLIB_ROOT=...
if(NOT GLIB_ROOT)
    set(GLIB_ROOT /usr)
endif()

# 自动检测 glib 库（.so 或 .a）
# Collect all dependency roots (glib + pcre2 + zlib + menu-cache)
set(ALL_ROOTS ${GLIB_ROOT})
foreach(root ${DEPS_ROOTS})
    list(APPEND ALL_ROOTS ${root})
endforeach()

# Find all needed static libraries
find_library(LIB_glib NAMES glib-2.0 PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_gobject NAMES gobject-2.0 PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_gio NAMES gio-2.0 PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_gthread NAMES gthread-2.0 PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_gmodule NAMES gmodule-2.0 PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_intl NAMES intl PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_ffi NAMES ffi PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_m NAMES m)
find_library(LIB_pcre2 NAMES pcre2-8 PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_z NAMES z PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)
find_library(LIB_menu_cache NAMES menu-cache PATHS ${ALL_ROOTS} PATH_SUFFIXES lib NO_DEFAULT_PATH)

if(NOT LIB_glib)
    message(FATAL_ERROR "libglib-2.0 not found")
endif()

set(GLIB_LIBRARIES ${LIB_glib} ${LIB_gobject} ${LIB_gio} ${LIB_gthread})
if(LIB_gmodule)
    list(APPEND GLIB_LIBRARIES ${LIB_gmodule})
endif()
if(LIB_ffi)
    list(APPEND GLIB_LIBRARIES ${LIB_ffi})
endif()
if(LIB_intl)
    list(APPEND GLIB_LIBRARIES ${LIB_intl})
endif()
if(LIB_m)
    list(APPEND GLIB_LIBRARIES ${LIB_m})
endif()
if(LIB_pcre2)
    list(APPEND GLIB_LIBRARIES ${LIB_pcre2})
endif()
if(LIB_z)
    list(APPEND GLIB_LIBRARIES ${LIB_z})
endif()
if(LIB_menu_cache)
    list(APPEND GLIB_LIBRARIES ${LIB_menu_cache})
endif()

# Collect include dirs from all deps
# gio-unix-2.0: gio/gdesktopappinfo.h required by base/fm-app-info.c etc.
set(ALL_INCLUDE_DIRS
    ${GLIB_ROOT}/include
    ${GLIB_ROOT}/include/glib-2.0
    ${GLIB_ROOT}/lib/glib-2.0/include
    ${GLIB_ROOT}/include/gio-unix-2.0
)
foreach(root ${DEPS_ROOTS})
    list(APPEND ALL_INCLUDE_DIRS ${root}/include)
endforeach()

# ---------------------------------------------------------------------------
# Target 1: fm — full libfm core library (base + job + extra), no GTK parts.
# Sources per upstream src/Makefile.am libfm_SOURCES (udisks disabled).
# ---------------------------------------------------------------------------
set(LIBFM_CORE_SOURCES
    src/fm.c
    src/glib-compat.c
    # base/ (upstream base_SOURCES, 24 files)
    src/base/fm-action.c
    src/base/fm-app-info.c
    src/base/fm-archiver.c
    src/base/fm-bookmarks.c
    src/base/fm-config.c
    src/base/fm-dummy-monitor.c
    src/base/fm-file.c
    src/base/fm-file-info.c
    src/base/fm-file-launcher.c
    src/base/fm-folder.c
    src/base/fm-folder-config.c
    src/base/fm-icon.c
    src/base/fm-list.c
    src/base/fm-mime-type.c
    src/base/fm-module.c
    src/base/fm-monitor.c
    src/base/fm-nav-history.c
    src/base/fm-path.c
    src/base/fm-templates.c
    src/base/fm-terminal.c
    src/base/fm-thumbnail-loader.c
    src/base/fm-thumbnailer.c
    src/base/fm-utils.c
    # job/ (upstream job_SOURCES, 9 files)
    src/job/fm-deep-count-job.c
    src/job/fm-dir-list-job.c
    src/job/fm-file-info-job.c
    src/job/fm-file-ops-job.c
    src/job/fm-file-ops-job-change-attr.c
    src/job/fm-file-ops-job-delete.c
    src/job/fm-file-ops-job-xfer.c
    src/job/fm-job.c
    src/job/fm-simple-job.c
    # extra/ (libfm-extra is part of upstream libfm.la too)
    src/extra/fm-xml-file.c
    # pre-generated (upstream glib-genmarshal output)
    generated/fm-marshal.c
)

add_library(fm SHARED ${LIBFM_CORE_SOURCES})
set_target_properties(fm PROPERTIES
    VERSION 4.0.2
    SOVERSION 4
    OUTPUT_NAME fm
)

target_include_directories(fm
    PUBLIC
        ${ALL_INCLUDE_DIRS}
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/src
        ${CMAKE_CURRENT_SOURCE_DIR}/src/base
        ${CMAKE_CURRENT_SOURCE_DIR}/src/job
        ${CMAKE_CURRENT_SOURCE_DIR}/generated
        ${CMAKE_CURRENT_BINARY_DIR}
)

target_compile_definitions(fm PRIVATE HAVE_CONFIG_H GETTEXT_PACKAGE="libfm")
target_link_libraries(fm ${GLIB_LIBRARIES})
# CMake ignores SOVERSION for soname on this platform — set it explicitly.
# glib/gobject/gio/gthread/gmodule symbols stay EXPORTED: consumers linking
# -lfm must resolve glib APIs against the SAME glib instance inside
# libfm.so (two static glib copies = split GType system, breaks GObject
# signals at runtime). Non-PIC archives (conan zlib/pcre2/ffi/intl and
# menu-cache — none carry a GType) are hidden instead: without excluding
# them lld rejects their non-PIC relocations when linking the shared lib.
target_link_options(fm PRIVATE "LINKER:-soname,libfm.so.4"
    "LINKER:--exclude-libs,libz.a:libpcre2-8.a:libffi.a:libintl.a:libmenu-cache.a")
target_compile_options(fm PRIVATE -pthread)

# Core headers: fm.h + base/ + job/ (+ pre-generated fm-marshal.h)
# Upstream fm.h uses flat #include "fm-app-info.h" — install all headers
# flat into include/libfm-4 (same layout as upstream libfm.pc includedir).
set(LIBFM_CORE_HEADERS
    ${CMAKE_CURRENT_SOURCE_DIR}/src/fm.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/fm-seal.h
)
file(GLOB LIBFM_BASE_HEADERS ${CMAKE_CURRENT_SOURCE_DIR}/src/base/*.h)
file(GLOB LIBFM_JOB_HEADERS ${CMAKE_CURRENT_SOURCE_DIR}/src/job/*.h)
install(TARGETS fm LIBRARY DESTINATION lib)
install(FILES ${LIBFM_CORE_HEADERS} DESTINATION include/libfm-4)
install(FILES ${LIBFM_BASE_HEADERS} DESTINATION include/libfm-4)
install(FILES ${LIBFM_JOB_HEADERS} DESTINATION include/libfm-4)
install(FILES generated/fm-marshal.h DESTINATION include/libfm-4)

# Generate fm-version.h from .in template
set(FM_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
set(FM_VERSION_MINOR ${PROJECT_VERSION_MINOR})
set(FM_VERSION_MICRO ${PROJECT_VERSION_PATCH})
configure_file(src/fm-version.h.in ${CMAKE_CURRENT_BINARY_DIR}/fm-version.h @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/fm-version.h DESTINATION include/libfm-4)

# ---------------------------------------------------------------------------
# Target 2: fm-extra — standalone libfm-extra sub-library (upstream parity,
# soname libfm-extra.so.4, pkg-config libfm-extra.pc)
# ---------------------------------------------------------------------------
set(LIBFM_EXTRA_SOURCES
    src/extra/fm-xml-file.c
)

set(LIBFM_EXTRA_HEADERS
    src/fm-extra.h
    src/extra/fm-xml-file.h
)

add_library(fm-extra SHARED ${LIBFM_EXTRA_SOURCES})
set_target_properties(fm-extra PROPERTIES
    VERSION 4.1.3
    SOVERSION 4
    OUTPUT_NAME fm-extra
)

target_include_directories(fm-extra
    PUBLIC
        ${ALL_INCLUDE_DIRS}
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/extra
        ${CMAKE_CURRENT_SOURCE_DIR}/src
        ${CMAKE_CURRENT_BINARY_DIR}
)

target_compile_definitions(fm-extra PRIVATE GETTEXT_PACKAGE="libfm-extra")
target_link_libraries(fm-extra ${GLIB_LIBRARIES})
target_link_options(fm-extra PRIVATE "LINKER:-soname,libfm-extra.so.4" "LINKER:--exclude-libs,ALL")
target_compile_options(fm-extra PRIVATE -pthread)

install(TARGETS fm-extra LIBRARY DESTINATION lib)
install(FILES ${LIBFM_EXTRA_HEADERS} DESTINATION include/libfm-4)

# pkg-config files (libfm.pc mirrors upstream libfm.pc.in Requires)
set(PACKAGE_VERSION ${PROJECT_VERSION})
set(prefix ${CMAKE_INSTALL_PREFIX})
set(exec_prefix ${prefix})
set(libdir ${prefix}/lib)
set(includedir ${prefix}/include/libfm-4)
set(FMINCLUDEADD -I${includedir})
configure_file(libfm-extra.pc.in ${CMAKE_CURRENT_BINARY_DIR}/libfm-extra.pc @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/libfm-extra.pc DESTINATION lib/pkgconfig)

# libfm.pc — upstream equivalent: Libs/Requires cover the core library
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/libfm.pc
"prefix=${prefix}
libdir=${libdir}
includedir=${includedir}

Name: libfm
Description: GLib-based library for file managers (core, no GTK)
Version: ${PACKAGE_VERSION}
Requires.private: glib-2.0 gobject-2.0 gio-2.0
Libs: -L\${libdir} -lfm
Cflags: -I\${includedir}
")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/libfm.pc DESTINATION lib/pkgconfig)
