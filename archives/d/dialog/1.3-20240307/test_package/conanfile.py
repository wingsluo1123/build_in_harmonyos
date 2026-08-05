#!/usr/bin/env python3
"""Conan test_package — dialog 1.3-20240307.

R34: test executes the dialog binary to verify functionality.
The test runs `dialog --version` and verifies the output matches the
expected version string.
"""
import os

from conan import ConanFile


class DialogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def build(self):
        pass

    def test(self):
        # R34: Execute the dialog binary to verify the package works
        # dialog --version prints "Version: 1.3-20240307"
        bin_path = os.path.join(self.dependencies["dialog"].package_folder, "bin", "dialog")
        self.run(f'"{bin_path}" --version', env="conanrun")
