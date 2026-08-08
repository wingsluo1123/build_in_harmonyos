#!/usr/bin/env python3
"""Conan test_package for redict 7.3.0.

Compiles and runs a test that verifies redict-server binary is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RedictTestConan(ConanFile):
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
