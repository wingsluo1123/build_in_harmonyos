#!/usr/bin/env python3
"""Conan test_package — goaccess 1.10.2.

Verifies that the goaccess binary is correctly built and can report its
version. This is the L1 (smoke) test in the CI test hierarchy.

R34: test must exercise the actual built binary, not just print a string.
"""
import os

from conan import ConanFile


class GoaccessTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No compilation needed — we test the prebuilt goaccess binary
        pass

    def test(self):
        # R34: Exercise the actual goaccess binary
        bin_path = os.path.join(self.dependencies["goaccess"].package_folder, "bin", "goaccess")
        self.run(f'"{bin_path}" --version', env="conanrun")
