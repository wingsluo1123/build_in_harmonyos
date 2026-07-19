#!/usr/bin/env python3
"""Conan test_package — cdo 2.4.0.

R34: Test actually executes cdo binary to verify it works.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CdoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_dir = self.dependencies["cdo"].cpp_info.bindirs[0]
            bin_path = os.path.join(bin_dir, "cdo")
            self.run(f'"{bin_path}" --version', env="conanrun")
            self.run(f'"{bin_path}" --help', env="conanrun")