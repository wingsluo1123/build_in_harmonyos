#!/usr/bin/env python3
"""Test package for parole — verifies the installed application binary.

parole is a media player application (not a library). The test verifies
that the parole binary is installed and can be executed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ParoleTestConan(ConanFile):
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
        # Run the test binary that validates parole's dependency chain
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_parole")
        self.run(f"{test_bin}", env="conanrun")
