#!/usr/bin/env python3
"""Consumer test for qtconnectivity (Bluetooth + NFC) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtconnectivityTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtconnectivity"].package_folder
        # Qt6Config lives in the qtbase package; the Qt6Bluetooth/Qt6Nfc
        # configs live in the qtconnectivity package.  Qt only searches the
        # additional prefixes listed in QT_ADDITIONAL_PACKAGES_PREFIX_PATH.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = pkg
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindirs = self.cpp.build.bindirs
        exe = os.path.join(bindirs[0] if bindirs else self.build_folder,
                           "test_qtconnectivity")
        self.run('"%s"' % exe, env="conanrun")
