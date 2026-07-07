#!/usr/bin/env python3
"""Conan test_package — libqalculate 5.11.0.

Tests that the libqalculate package can be found, compiled against,
and linked successfully on OpenHarmony.

File location: archives/{letter}/libqalculate/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibqalculateTestConan(ConanFile):
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
        # Explicit self.run() — CI L0d requires a direct call in test()
        bin_path = os.path.join(self.build_folder, "test_libqalculate")
        self.run(f'"{bin_path}"', env="conanrun")
