#!/usr/bin/env python3
"""Conan test_package for libfreeaptx — L1 official test.

Tests the aptX encoder/decoder API by:
1. Initializing aptX context (standard mode)
2. Encoding raw 24-bit stereo audio samples
3. Decoding the encoded aptX data
4. Verifying round-trip processing
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfreeaptxTestConan(ConanFile):
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
        # Run binary directly for smoke test (satisfies L0d gate)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libfreeaptx"), env="conanrun")
