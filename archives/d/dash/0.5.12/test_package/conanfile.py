#!/usr/bin/env python3
"""Conan test_package — dash 0.5.12

Tests that the dash binary is installed and functional.
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
        # Test dash binary directly — dash has no --version flag, use -c to run a command
        dash_bin = os.path.join(self.dependencies["dash"].package_folder, "bin", "dash")
        self.run(f'"{dash_bin}" -c "exit 0"')
