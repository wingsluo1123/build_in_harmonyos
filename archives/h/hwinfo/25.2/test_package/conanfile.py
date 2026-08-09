#!/usr/bin/env python3
"""Conan test_package for hwinfo — verifies the hwinfo binary works."""
import os

from conan import ConanFile


class HwinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must execute the tested package's binary
        bin_path = os.path.join(self.dependencies["hwinfo"].package_folder, "bin", "hwinfo")
        self.run(f'"{bin_path}" --version', env="conanrun")
