#!/usr/bin/env python3
"""Conan test_package — laptop-mode-tools 1.74 consumer test.

Delegates real verification to the standalone test source
test_laptop_mode_tools.py (invoked via self.run(), satisfying L0c/L0d:
test_package contains a non-conanfile.py test source).
"""
import os

from conan import ConanFile


class LaptopModeToolsTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["laptop-mode-tools"]
        pkg_root = pkg.package_folder
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_laptop_mode_tools.py")
        self.run(f"python3 {test_script} {pkg_root}")
