#!/usr/bin/env python3
"""Conan test_package for spim — verifies the spim binary works.

Uses CMake to build a test program that invokes the spim binary
with a simple MIPS assembly program (test_hello.s).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SpimTestConan(ConanFile):
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
        # Run the test executable directly via self.run() (L0d requirement)
        cmake = CMake(self)
        test_bin = os.path.join(cmake.build_folder, "test_spim")
        self.run(f'"{test_bin}"', env="conanrun")
