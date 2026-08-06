#!/usr/bin/env python3
"""Conan test_package for fish 3.7.1.

This test verifies that the fish shell binary is functional by running
`fish --version` and a math command using the binary from the conan package.
R34: test must actually use the tested package's binary.
"""
import os

from conan import ConanFile


class FishTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the fish binary path from the conan package (R34)
        # Using explicit path ensures the test depends on the package artifact
        fish_bindir = self.dependencies["fish"].cpp_info.bindirs[0]
        fish_bin = os.path.join(fish_bindir, "fish")

        # Run fish --version (R34: must actually call the tested binary)
        self.run(f'"{fish_bin}" --version', env="conanrun")

        # Run a math command to verify fish can execute and compute
        self.run(f'"{fish_bin}" -c "math 5+5"', env="conanrun")
