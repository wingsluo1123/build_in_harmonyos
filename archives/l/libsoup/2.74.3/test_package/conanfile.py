#!/usr/bin/env python3
"""Conan test_package for libsoup 2.74.3.

Verifies that libsoup can be linked and its API is callable.
Uses CMake to build a simple test that creates a SoupMessage.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsoupTestConan(ConanFile):
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
