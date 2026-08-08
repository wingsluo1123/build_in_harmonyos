#!/usr/bin/env python3
"""Conan recipe for audiocd-kio 26.04.1 on HarmonyOS PC.

audiocd-kio is a KDE KIO slave for audio CDs. It provides the kio_audiocd
plugin and the audiocdplugins shared library for encoding CD audio to
FLAC, Vorbis, or WAV formats.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
  - BUILD_TESTING=OFF to skip upstream tests during Conan build
  - KCMUtils made OPTIONAL (kcmaudiocd module disabled - kcmutils_generate_desktop_file not available)
  - DocTools disabled (kdoctools_create_handbook not available)
  - lame encoder disabled (lame library not available)
  - Opus made conditional (find_package(Opus))
  - kconfig_compiler_kf6 generated files pre-supplied via patches (0003-0006)
  - Dependencies: qtbase/6.11.1, ecm/6.20.0, flac/1.4.3, libvorbis/1.3.7
  - KF6 framework packages (Config, I18n, KIO, Solid, WidgetsAddons) required
  - libkcddb and cdparanoia also required
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AudiocdKioConan(ConanFile):
    name = "audiocd-kio"
    version = "26.04.1"
    description = "KDE KIO slave for audio CDs with encoding plugins (FLAC, Vorbis, WAV)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/multimedia/audiocd-kio"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("flac/1.4.3")
        self.requires("libvorbis/1.3.7")
        # Resolve libogg version conflict: flac wants 1.3.5, libvorbis wants 1.3.6
        self.requires("libogg/1.3.6", override=True)
        # KF6 framework packages — required by CMakeLists.txt
        # These are not yet published to the conan repo
        self.requires("cdparanoia/10.2")
        self.requires("kconfig/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("solid/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        # kdbusaddons/6.14.0 — blocked: requires Qt6DBus (not available, qtbase built with FEATURE_dbus=OFF)
        # kservice/6.14.0 — depends on ki18n (available), can be built after kdbusaddons
        # kio/6.14.0 — depends on kdbusaddons (blocked by Qt6DBus)
        # libkcddb/26.04.1 — depends on kio (blocked by Qt6DBus dependency chain)

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

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Set QUERY_EXECUTABLE for ECMQueryQt to bypass Qt6::qtpaths target lookup
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            tc.variables["QUERY_EXECUTABLE"] = qtpaths6
            tc.variables["_cli_option"] = "--query"

        tc.generate()

        # qtbase uses cmake_find_mode=none, so CMakeDeps doesn't generate
        # conan_cmakedeps_paths.cmake. Create it manually.
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
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")'
            )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
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
        # audiocd-kio installs kio_audiocd plugin and audiocdplugins library
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["audiocdplugins"]
