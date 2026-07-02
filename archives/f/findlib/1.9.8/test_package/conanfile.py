#!/usr/bin/env python3
"""Conan test_package — findlib (ocamlfind) 1.9.8

Verifies that ocamlfind is installed and can query packages.
"""
import os

from conan import ConanFile


class FindlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # ocamlfind should be in PATH via cpp_info.bindirs
        bin_dir = os.path.join(self.dependencies["findlib"].package_folder, "bin")
        ocamlfind = os.path.join(bin_dir, "ocamlfind")
        self.run(f'"{ocamlfind}" query findlib -format "%v"', env="conanrun")
