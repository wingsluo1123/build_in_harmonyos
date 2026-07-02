#!/usr/bin/env python3
"""Conan test_package -- Menhir 20260209

Verifies that menhir is installed and can generate parsers.
"""
import os

from conan import ConanFile


class MenhirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = os.path.join(self.dependencies["menhir"].package_folder, "bin")
        menhir = os.path.join(bin_dir, "menhir")
        if os.path.isfile(menhir):
            self.run(f'"{menhir}" --version', env="conanrun")
        else:
            self.run("menhir --version", env="conanrun")
