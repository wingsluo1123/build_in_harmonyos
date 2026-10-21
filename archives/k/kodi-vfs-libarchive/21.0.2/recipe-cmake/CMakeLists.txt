# Standalone build entry for the unmodified upstream sources of
# vfs.libarchive 21.0.2-Omega on OHOS.
#
# The upstream CMakeLists.txt needs find_package(Kodi) + build_addon()
# from the kodi-addon-dev distribution (not packaged on the ohpcd registry).
# This entry builds the same sources with the recipe-provided Kodi SDK
# include tree, replicating the parts of the upstream flow that matter:
#   - module target named vfs.libarchive with PREFIX "" (build_addon), so the
#     artifact is vfs.libarchive.so = addon.xml.in library_@PLATFORM@'s
#     @LIBRARY_FILENAME@
#   - the upstream-closed libarchive dependency resolved against the Conan
#     libarchive package instead of the static bundled build (the add-on
#     source only calls the libarchive public API, archive.h/archive_entry.h)
#   - POSITION_INDEPENDENT_CODE (build_addon sets it for the shared module;
#     a MODULE target compiles its sources with -fPIC automatically)
# Upstream sources are consumed unmodified from ../src (ADDON_SRC_DIR).
# Upstream's -DLIBARCHIVE_STATIC/-D_CRT_NONSTDC_NO_DEPRECATE add_definitions
# only affect Windows declspec/deprecation branches and are irrelevant on
# OHOS/clang, so they are not redefined here.
#
# A VFS add-on has no GL/EGL render path (it only serves file/entry listings
# through host callbacks), so — unlike the screensaver add-on — no HAS_GLES /
# GLESv3 / EGL setup is needed here.
cmake_minimum_required(VERSION 3.5)
project(vfs.libarchive C CXX)

# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources
#                          (src/, LICENSE.md, vfs.libarchive/)
#   KODI_SDK_INCLUDE_DIR - kodi-dev-kit include tree (provides kodi/ headers)

set(VFS_ADDON_SOURCES ${ADDON_SRC_DIR}/src/ArchiveFile.cpp)

find_package(libarchive CONFIG REQUIRED)

add_library(${PROJECT_NAME} MODULE ${VFS_ADDON_SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

target_include_directories(${PROJECT_NAME} PRIVATE
                           ${ADDON_SRC_DIR}
                           ${KODI_SDK_INCLUDE_DIR})
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
# Explicit DT_NEEDED closure (musl dlopen resolves only the module's own
# DT_NEEDED closure, knowledge E004 BIND_NOW + lcmaps-plugins-basic
# experience entry): the module explicitly links the shared libarchive, whose
# own zstd dependency stays a dynamic NEEDED of libarchive.so.
target_link_libraries(${PROJECT_NAME} PRIVATE libarchive::archive)
