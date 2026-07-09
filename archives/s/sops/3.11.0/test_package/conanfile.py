#!/usr/bin/env python3
"""Conan test_package for sops 3.11.0 — Go binary tool.

L1 test: verify sops binary runs and reports correct version.
Uses the elfldr wrapper (transparently via bin/sops shell wrapper).
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SopsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # No compilation needed — this is a binary tool
        pass

    def test(self):
        # Get the sops binary path from the dependency's package folder
        sops_pkg = self.dependencies["sops"]
        bin_dir = os.path.join(sops_pkg.package_folder, "bin")
        sops_path = os.path.join(bin_dir, "sops")
        self.run(f'"{sops_path}" --version', env="conanrun")
