#!/usr/bin/env python3
"""Conan test_package — qalculate-gtk 5.11.0.

Verifies that the qalculate-gtk package correctly brings in libqalculate
as a transitive dependency. The test program includes libqalculate headers
and links the library to confirm the dependency chain is intact.

File location: archives/q/qalculate-gtk/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QalculateGtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 fix: CMake does not recognise HarmonyOS as a target platform.
        # Force CMAKE_SYSTEM_NAME=Linux so CMake uses the standard Linux
        # platform module instead of aborting on "unknown system".
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
