#!/usr/bin/env python3
"""Conan test_package for mold 2.39.1.

Verifies that the mold binary is installed and functional by running
`mold --version`. Also builds a trivial C program to exercise the
CMake toolchain integration.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MoldTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # R34: Execute the packaged binary to verify it works
        self.run("mold --version", env="conanrun")
