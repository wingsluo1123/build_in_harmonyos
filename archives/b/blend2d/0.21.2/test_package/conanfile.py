#!/usr/bin/env python3
"""Conan test_package for Blend2D — C API smoke test.

Verifies that the blend2d library can be loaded and its C API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Blend2DTestConan(ConanFile):
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
        # Run the test binary directly with Conan's run environment
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_blend2d")
        self.run(test_bin, env="conanrun")
