#!/usr/bin/env python3
"""Conan test_package for fatsort 1.7.1.683."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FatsortTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["fatsort"].package_folder, "bin", "fatsort")
        if not os.path.isfile(bin_path):
            raise Exception(f"fatsort binary not found: {bin_path}")
        if can_run(self):
            self.run(f"{bin_path} -v", env="conanrun")
            self.run(f"{bin_path} -h", env="conanrun")
