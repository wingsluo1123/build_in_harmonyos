#!/usr/bin/env python3
"""Conan test_package for diffutils 3.10

Tests that diff binary is installed and functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DiffutilsTestConan(ConanFile):
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
        diff_bin = os.path.join(self.dependencies["diffutils"].package_folder, "bin", "diff")
        self.run(f"{diff_bin} --version")
