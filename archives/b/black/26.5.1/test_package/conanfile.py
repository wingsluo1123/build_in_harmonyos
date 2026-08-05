#!/usr/bin/env python3
"""Conan test_package for black 26.5.1.

R34: test must substantively depend on the package under test.
black is a console application (entry point: black = black:patched_main).
We invoke the installed `black --version` to verify the wrapper and package layout work.
"""
import os

from conan import ConanFile


class BlackTestConan(ConanFile):
    # Pure Python application test, no CMake needed
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: substantively depend on the package under test — call bin/black --version
        black_dep = self.dependencies["black"]
        black_bin = os.path.join(black_dep.package_folder, "bin", "black")
        self.run(f'"{black_bin}" --version', env="conanrun")
