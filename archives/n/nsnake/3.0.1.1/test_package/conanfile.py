#!/usr/bin/env python3
"""Consumer tests for the packaged nsnake executable."""
import os

from conan import ConanFile


class NsnakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["nsnake"].package_folder, "bin", "nsnake"
        )
        self.run(f"{executable} --version", env="conanrun")
        self.run(f"{executable} --help", env="conanrun")
