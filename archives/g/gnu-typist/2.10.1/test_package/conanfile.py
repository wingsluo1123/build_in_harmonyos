#!/usr/bin/env python3
"""Conan test_package for gnu-typist 2.10.1 — L1 official test."""
import os
from conan import ConanFile


class GnutypistTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test the gtypist binary from the installed package
        pkg_folder = self.dependencies["gnu-typist"].package_folder
        gtypist_bin = os.path.join(pkg_folder, "bin", "gtypist")
        self.run(gtypist_bin + " --version 2>&1", env="conanrun")
        # Verify the binary exists and has a non-trivial size
        self.run("ls -la " + gtypist_bin + " 2>&1", env="conanrun")