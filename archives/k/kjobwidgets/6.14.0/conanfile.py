#!/usr/bin/env python3
"""Conan recipe for kjobwidgets 6.14.0 on HarmonyOS PC.

KJobWidgets is a KDE Frameworks 6 library for tracking KJob progress with widgets.
It provides the KF6JobWidgets library.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
  - BUILD_TESTING=OFF to skip upstream tests
  - USE_DBUS=OFF (DBus not available on OHOS)
  - ECM_MODULE_PATH set manually for CMakeDeps compatibility
  - QUERY_EXECUTABLE set to qtpaths6 for ECMQueryQt
  - conan_cmakedeps_paths.cmake created manually (qtbase cmake_find_mode=none)
  - KF6Notifications made optional (not in conan cache)
  - ECMPoQmTools disabled (Qt6LinguistTools not available)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KjobwidgetsConan(ConanFile):
    name = "kjobwidgets"
    version = "6.14.0"
    description = "KDE Frameworks 6 job widgets library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kjobwidgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["WITH_X11"] = "OFF"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            tc.variables["QUERY_EXECUTABLE"] = qtpaths6
            tc.variables["_cli_option"] = "--query"

        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        ecm_dep = self.dependencies.build.get("ecm")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm_dep:
                ecm_pkg = ecm_dep.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
            # Add kcoreaddons cmake dir
            kcoreaddons = self.dependencies.get("kcoreaddons")
            if kcoreaddons:
                kc_pkg = kcoreaddons.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{kc_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{kc_pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{kc_pkg}/include")')
            # Add kwidgetsaddons cmake dir
            kwidgetsaddons = self.dependencies.get("kwidgetsaddons")
            if kwidgetsaddons:
                kw_pkg = kwidgetsaddons.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{kw_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{kw_pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{kw_pkg}/include")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6JobWidgets"]
