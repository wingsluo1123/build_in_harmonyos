#!/usr/bin/env python3
"""Conan test_package for lmdbxx — exercises the C++17 LMDB wrapper API.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LmdbxxTestConan(ConanFile):
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
        # Explicitly run the test binary for direct verification
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lmdbxx"), env="conanrun")
