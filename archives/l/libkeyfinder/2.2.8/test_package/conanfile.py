#!/usr/bin/env python3
"""Conan test_package — libkeyfinder 2.2.8

Tests the libkeyfinder API by creating an AudioData object with silence
and calling keyOfAudio(), verifying it returns SILENCE.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibkeyfinderTestConan(ConanFile):
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
        # Run the test binary directly with conanrun env to ensure
        # shared libraries are found via LD_LIBRARY_PATH
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libkeyfinder")
        self.run(test_bin, env="conanrun")
