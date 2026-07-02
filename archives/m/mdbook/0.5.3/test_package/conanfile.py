#!/usr/bin/env python3
"""Conan test_package — mdBook v0.5.3.

L1 test: verify the mdbook binary is functional.
Runs `mdbook --version` to confirm the binary is executable.
"""
import os

from conan import ConanFile


class MdbookTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build step needed for a binary tool test
        pass

    def test(self):
        # L2 smoke test: run mdbook --version
        bin_path = os.path.join(self.dependencies["mdbook"].package_folder, "bin", "mdbook")
        self.run(f'"{bin_path}" --version', env="conanrun")
