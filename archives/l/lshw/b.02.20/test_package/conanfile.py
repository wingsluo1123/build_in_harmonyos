#!/usr/bin/env python3
"""Conan test_package for lshw B.02.20.

R34: Test must actually depend on the tested package.
lshw is a CLI tool — the test runs `lshw -version` to verify
the binary works correctly.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LshwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary
        dep = self.dependencies["lshw"]
        lshw_bin = os.path.join(dep.package_folder, "bin", "lshw")
        if can_run(self):
            self.run(f'"{lshw_bin}" -version', env="conanrun")
