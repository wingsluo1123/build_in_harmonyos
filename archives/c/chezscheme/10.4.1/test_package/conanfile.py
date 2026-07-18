#!/usr/bin/env python3
"""Conan test_package for chezscheme 10.4.1.

Tests the scheme interpreter by running it with Scheme expressions.
This is the L1 test in the five-level test system.
R34: test must substantively depend on the tested package — uses
explicit conan package binary path, not system PATH lookup.
"""
import os

from conan import ConanFile


class ChezschemeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for interpreter test

    def test(self):
        # R34: Use explicit path to conan-provided binary
        # Ensures test fails when package artifacts are sabotaged (L1e)
        # Avoids system PATH fallback finding a manually-installed scheme
        pkg_folder = self.dependencies["chezscheme"].package_folder
        scheme_bin = os.path.join(pkg_folder, "bin", "scheme")

        # Run test.sh wrapper (also serves as L0c test source file)
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'"{test_script}" "{scheme_bin}"', env="conanrun")
