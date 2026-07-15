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
            bin_path = os.path.join(self.cpp.build.bindirs[0], "cdo")
            self.run(f"{bin_path} --version", env="conanrun")
            self.run(f"{bin_path} --help", env="conanrun")