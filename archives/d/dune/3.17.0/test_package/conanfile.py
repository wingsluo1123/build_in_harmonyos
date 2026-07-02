#!/usr/bin/env python3
"""Conan test_package -- Dune 3.17.0

Verifies that dune is installed and can report its version.
"""
import os

from conan import ConanFile


class DuneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = os.path.join(self.dependencies["dune"].package_folder, "bin")
        dune = os.path.join(bin_dir, "dune")
        if os.path.isfile(dune):
            self.run(f'"{dune}" --version', env="conanrun")
        else:
            self.run("dune --version", env="conanrun")
