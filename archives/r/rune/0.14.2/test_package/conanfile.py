#!/usr/bin/env python3
"""Conan consumer test for the Rune command-line interpreter."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RuneTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["rune"].package_folder
        executable = os.path.join(package_folder, "bin", "rune")
        assert os.path.isfile(executable), f"rune binary not found: {executable}"

        if can_run(self):
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'zsh "{script}" "{executable}"', env="conanrun")
        else:
            with open(executable, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "rune is not an ELF binary"
