#!/usr/bin/env python3
"""Conan test_package — dash 0.5.12

Tests that the dash binary is installed and functional.
Verifies arithmetic, variables, conditionals, and loops.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DashTestConan(ConanFile):
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
        dash_bin = os.path.join(self.dependencies["dash"].package_folder, "bin", "dash")
        # Run the compiled test program with dash binary path as argument
        test_exe = os.path.join(self.build_folder, "test_dash")
        self.run(f'"{test_exe}" "{dash_bin}"')
