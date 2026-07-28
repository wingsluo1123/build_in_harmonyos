#!/usr/bin/env python3
"""Conan test_package — tinyxml2 10.0.0 L1 smoke test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Tinyxml2TestConan(ConanFile):
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
