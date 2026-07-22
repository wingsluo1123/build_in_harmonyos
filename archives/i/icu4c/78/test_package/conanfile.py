#!/usr/bin/env python3
"""Conan test_package for icu4c — tests real ICU API (R34)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Icu4CTestConan(ConanFile):
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
        # Run the test binary directly instead of cmake.test()
        # (CMakeLists.txt doesn't have enable_testing())
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_icu4c")
        self.run(test_bin, env="conanrun")
