#!/usr/bin/env python3
"""Conan test_package for pnc-gawk: load the packaged gawkpn.so with GNU Awk
and run the HarmonyOS-native checks on the packaged extension."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PncGawkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PNC_GAWK_PACKAGE_DIR"] = \
            self.dependencies[self.tested_reference_str].package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("test_package: target binaries cannot execute here, skipped")
            return
        extension_dir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "lib", "gawk"
        )
        gawk = os.path.join(self.dependencies["gawk"].package_folder, "bin", "gawk")
        script = os.path.join(self.source_folder, "test_gawkpn.awk")
        # Functional test: GNU Awk loads the packaged extension and every
        # exported AWK function is exercised (see test_gawkpn.awk).
        self.run('AWKLIBPATH="%s" "%s" -l gawkpn -f "%s"'
                 % (extension_dir, gawk, script))
        # HarmonyOS-native checks on the packaged artifact.
        self.run('PNC_GAWK_EXTENSION_DIR="%s" "%s"'
                 % (extension_dir, os.path.join(self.cpp.build.bindirs[0], "test_ohos")))
