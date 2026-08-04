#!/usr/bin/env python3
"""Conan test_package for aircrack-ng — verifies installed binaries.

R34: Test must exercise the actual binary (not a stub).
Runs smoke test script that verifies binary presence and version output.
"""
import os
from conan import ConanFile


class AircrackngTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["aircrack-ng"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        self.run(f"bash test_aircrack_ng.sh {bin_dir}", env="conanrun")
        self.output.info("aircrack-ng: OK")
