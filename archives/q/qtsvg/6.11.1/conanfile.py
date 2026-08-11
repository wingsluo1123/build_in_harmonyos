#!/usr/bin/env python3
"""Conan recipe for qtsvg 6.11.1 on HarmonyOS PC.

qtsvg is the Qt6 SVG module, providing Qt6Svg and Qt6SvgWidgets shared
libraries (SVG rendering + SVG widget integration).

OHOS-specific adaptations:
  - Depends on qtbase/6.11.1 (Qt6Core/Qt6Gui/Qt6Widgets), which is already
    published to ohpcd and built for armv8 (aarch64-linux-ohos).
  - qtbase uses cmake_find_mode=none, so CMakeDeps does not generate
    conan_cmakedeps_paths.cmake. We create it manually to add qtbase's
    lib/cmake to CMAKE_PREFIX_PATH so find_package(Qt6) resolves.
  - BUILD_SHARED_LIBS=ON: Qt6 modules are shared libraries managed by Conan
    dependency chain (qtbase already ships its own shared libs).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtsvgConan(ConanFile):
    name = "qtsvg"
    version = "6.11.1"
    description = "Qt6 SVG module (Qt6Svg / Qt6SvgWidgets)"
    license = "LGPL-3.0-only"
    homepage = "https://code.qt.io/cgit/qt/qtsvg.git"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        # Qt6 module builds need the qmake/Qt tooling from qtbase at build time
        tc.variables["QT_HOST_PATH"] = ""

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # Point Qt's build internals at qtbase's installed
            # Qt6BuildInternals so qt_internal_project_setup() runs in
            # standalone-module mode (produces versioned SONAMEs and
            # libQt6Svg.so.6 symlinks instead of in-tree relative links).
            build_internals = os.path.join(
                qt_pkg, "lib", "cmake", "Qt6BuildInternals"
            )
            if os.path.isdir(build_internals):
                tc.cache_variables["QT_BUILD_INTERNALS_PATH"] = (
                    build_internals
                )
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Project installs its own Qt6SvgConfig.cmake / Qt6SvgWidgetsConfig.cmake
        # with proper dependency tracking; let CMakeDeps not shadow them.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["Qt6Svg", "Qt6SvgWidgets"]
