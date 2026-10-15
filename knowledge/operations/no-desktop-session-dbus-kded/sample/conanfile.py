#!/usr/bin/env python3
"""Conan recipe for the demo library of
knowledge/operations/no-desktop-session-dbus-kded/.

The demo builds the *same* KF6 session-services branch that kwrited uses:
the upstream CMakeLists drives BUILD_AS_EXECUTABLE through
cmake_dependent_option(.. OFF "KPty_HAVE_UTEMPTER" ON), so on OHOS - where
the kpty package is built with KPty_HAVE_UTEMPTER=FALSE - the standalone
executable branch is selected instead of the KDED/D-Bus plugin branch.

Two modes are used by reproduce.sh (same recipe, one environment switch):
  SAMPLE_ASSUME_DESKTOP_SESSION=1 -> pretend a desktop session exists (utempter
      present, KDED able to load the plugin): the sample forces
      BUILD_AS_EXECUTABLE=OFF *after* cmake_dependent_option(), the plugin
      branch is taken and find_package(KF6DBusAddons) fails (策略关闭 ->
      configure error, the evidence the knowledge doc refers to)
  SAMPLE_ASSUME_DESKTOP_SESSION unset -> CMake decides (ON), the executable
      branch builds and the demo runs without a session bus (策略开启 -> 生效)

conan_cmakedeps_paths.cmake is written by hand because the KF6/Qt6 recipes
of this archive use cmake_find_mode=none, which keeps CMakeDeps from adding
their lib/cmake dirs to CMAKE_PREFIX_PATH (kpty 6.26.0 / kwrited 6.7.2
precedent).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SessionStrategySampleConan(ConanFile):
    name = "session-strategy-sample"
    version = "0.1"
    description = ("Demo: KF6 session-services branch selection without a "
                   "D-Bus session bus / KDED")
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "CMakeLists.txt", "*.cpp", "*.json"

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("kpty/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = True
        tc.generate()

        # qtbase/KF6 use cmake_find_mode=none, so CMakeDeps does not generate
        # conan_cmakedeps_paths.cmake; write it so the toolchain (which
        # includes it optionally) points CMake at every dependency.
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        variables = {}
        if os.environ.get("SAMPLE_ASSUME_DESKTOP_SESSION"):
            # Demo switch: pretend the platform *does* have a desktop session
            # (utempter/utmp available, KDED present to load the plugin). The
            # sample's CMakeLists turns the switch into BUILD_AS_EXECUTABLE=OFF
            # after the cmake_dependent_option() call - which would otherwise
            # force ON, because the KF6Pty package exports
            # KPty_HAVE_UTEMPTER=FALSE as a plain (not cache) variable, so a
            # command line -DKPty_HAVE_UTEMPTER gets shadowed by the config.
            variables["SAMPLE_ASSUME_DESKTOP_SESSION"] = "ON"
        cmake.configure(variables=variables)
        cmake.build()
