#!/usr/bin/env python3
"""Conan test_package for zoxide 0.9.8 — smoke test via --version.

zoxide is a command-line tool, not a library. This test verifies
the packaged binary runs correctly via the elfldr wrapper.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ZoxideTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["zoxide"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        wrapper = os.path.join(bin_dir, "zoxide-wrapper")

        # Run the zoxide binary via the wrapper
        self.run(f'"{wrapper}" --version', env="conanrun")
