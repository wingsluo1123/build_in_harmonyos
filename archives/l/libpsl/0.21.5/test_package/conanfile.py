#!/usr/bin/env python3
"""Conan test_package for libpsl 0.21.5.

Verifies that libpsl can be linked and its API is callable.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibpslTestConan(ConanFile):
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
