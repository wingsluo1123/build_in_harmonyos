#!/usr/bin/env python3
"""Conan test_package — corepdf 1.0

Tests that the corepdf binary is installed and can start.
Since corepdf is a GUI application, we verify the binary exists
and can be invoked (it may fail on headless systems due to Qt
platform plugin, which is expected).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CorepdfTestConan(ConanFile):
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
        # Run the test binary which verifies the corepdf binary exists
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_corepdf"), env="conanrun")
