#!/usr/bin/env python3
"""test_package for astroterm 1.0.9.

R34: test_package must exercise the installed binary.
We run `astroterm --version` and `astroterm --help` as smoke tests.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["astroterm"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "astroterm")
        if can_run(self):
            self.run(f'"{bin_path}" --version', env="conanrun")
            self.run(f'"{bin_path}" --help', env="conanrun")
