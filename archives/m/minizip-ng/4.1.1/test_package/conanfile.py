#!/usr/bin/env python3
"""Conan test_package for minizip-ng — functional L1 test.

Creates a zip archive, extracts it, and verifies content integrity.
This exercises the core minizip-ng API (zip/unzip with zlib compression).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MinizipNgTestConan(ConanFile):
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
        # Run test binary directly (required by CI L0d gate)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_minizip_ng")
        self.run(test_bin, env="conanrun")
