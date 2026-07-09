#!/usr/bin/env python3
"""Conan test_package for just 1.43.1 — smoke test via --version.

just is a command-line tool, not a library. This test verifies
the packaged binary runs correctly via the elfldr wrapper.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class JustTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["just"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        wrapper = os.path.join(bin_dir, "just-wrapper")

        # Run the just binary via the wrapper
        self.run(f'"{wrapper}" --version', env="conanrun")
