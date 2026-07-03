#!/usr/bin/env python3
"""Conan test_package for aztfexport 0.19.0 — Go pure binary tool.

L1 smoke test: verify the aztfexport binary is installed and executable.
"""
import os
from conan import ConanFile


class AztfexportTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Smoke test: verify binary exists and shows version
        bin_path = os.path.join(self.dependencies["aztfexport"].package_folder, "bin", "aztfexport")
        assert os.path.isfile(bin_path), f"aztfexport binary not found at {bin_path}"
        self.run(f'"{bin_path}" --version || "{bin_path}" version || "{bin_path}" -v')
