#!/usr/bin/env python3
"""Conan test_package for kservice5 5.116.0.

Consumes KF5::Service through the Conan-generated CMake config and exercises
the public KService accessors on the installed package - not a bare header
include.

The KF5 dependencies are explicit requirements because the installed
KF5ServiceConfig.cmake does find_dependency on them, and kconfig5 /
kcoreaddons5 / kdbusaddons5 / ki18n5 publish cmake_find_mode=none: they are
only reachable through their own installed KF5*Config.cmake under
<prefix>/lib/cmake, so those prefixes have to be on CMAKE_PREFIX_PATH.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kservice5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("kconfig5/5.116.0")
        self.requires("kcoreaddons5/5.116.0.1")
        self.requires("kdbusaddons5/5.116.0")
        self.requires("ki18n5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        # No runtime path: CMake would rewrite it during install, and that
        # relink invalidates the OHOS .codesign of the packaged libraries. The
        # consumer finds them through LD_LIBRARY_PATH instead, which the OHOS
        # loader does honour - see the package conanfile.
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.generate()

        lines = []
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")'
                    % dep.package_folder
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        # The consumer's HarmonyOS-specific case builds a sycoca database with
        # the kbuildsycoca5 that ships inside this package, so it needs the
        # package's bin directory.
        tested = self.dependencies.get("kservice5")
        if tested and tested.package_folder:
            env.define("KSERVICE5_BIN_DIR",
                       os.path.join(tested.package_folder, "bin"))
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kservice5"),
                env="conanrun",
            )
