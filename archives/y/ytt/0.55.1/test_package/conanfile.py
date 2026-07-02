#!/usr/bin/env python3
"""Conan test_package — ytt 0.55.1 (Go binary).

L1 test: Verify the ytt binary is installed and runs correctly.
Runs `ytt --version` to check the binary is functional.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class YttTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the ytt binary path from the dependency's package
        ytt_pkg = self.dependencies["ytt"]
        bin_dir = ytt_pkg.cpp_info.bindirs[0]
        ytt_bin = os.path.join(bin_dir, "ytt")
        
        # Run ytt --version to verify the binary works
        self.run(f'"{ytt_bin}" --version', env="conanrun")
