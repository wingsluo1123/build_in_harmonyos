#!/usr/bin/env python3
"""Conan test_package — colordiff 1.0.22

Tests the colordiff binary by running --version.
colordiff is a Perl script tool, not a library, so we test the script directly.
"""
import os

from conan import ConanFile


class ColordiffTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a script tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["colordiff"].cpp_info.bindirs[0]
        colordiff_bin = os.path.join(bin_dir, "colordiff")

        # Run colordiff --version to verify the script works
        # colordiff wraps diff, so --version shows diff version
        self.run(f'"{colordiff_bin}" --version', env="conanrun")
