#!/usr/bin/env python3
"""Conan test_package for ktx 4.3.2 — verifies libktx is linkable and callable
from a *consumer* project (not from the build tree).

L1 test: call ktxTexture_CreateFromMemory() with invalid (0-byte) data and
require a non-KTX_SUCCESS return, which proves the real library code ran.

Note: test() uses self.run() rather than cmake.test().  The platform's L0d gate
requires a self.run() in test(); the 4.4.2 template hit the same thing.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KtxTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ktx"),
                 env="conanrun")
