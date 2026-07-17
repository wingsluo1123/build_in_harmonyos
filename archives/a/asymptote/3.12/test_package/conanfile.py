#!/usr/bin/env python3
"""Conan test_package for asymptote 3.12."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AsymptoteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        source = os.path.join(self.source_folder, "test_package.c")
        executable = os.path.join(self.build_folder, "test_package")
        compiler = os.environ.get("CC", "cc")
        self.run(f'{compiler} "{source}" -o "{executable}"')

    def test(self):
        if can_run(self):
            executable = os.path.join(self.build_folder, "test_package")
            self.run(f'"{executable}"', env="conanrun")
