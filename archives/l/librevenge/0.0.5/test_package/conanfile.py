#!/usr/bin/env python3
"""Test package for librevenge — verifies RVNGStringVector and RVNGPropertyList APIs."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # L0d: test() must include self.run() call
        self.run("ctest --output-on-failure")
