#!/usr/bin/env python3
"""Conan test_package — astroterm 1.0.9 CLI tool verification.

astroterm is a terminal tool, not a library. This test verifies
the binary is installed and can execute.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AstrotermTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            dep = self.dependencies["astroterm"]
            astroterm_bin = os.path.join(dep.package_folder, "bin", "astroterm")
            test_bin = os.path.join(self.build_folder, "test_astroterm")
            self.run(f'{test_bin} "{astroterm_bin}"', env="conanrun")
