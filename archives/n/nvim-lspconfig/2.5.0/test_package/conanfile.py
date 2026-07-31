#!/usr/bin/env python3
"""Conan test_package for nvim-lspconfig 2.5.0."""
import os
import sys

from conan import ConanFile


class NvimLspconfigTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["nvim-lspconfig"].package_folder
        root = os.path.join(pkg, "share", "nvim-lspconfig")
        script = os.path.join(self.recipe_folder, "test_nvim_lspconfig.py")
        self.run(f'"{sys.executable}" "{script}" "{root}"', env="conanrun")
