#!/usr/bin/env python3
"""Conan test_package for cdparanoia 10.2."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CdparanoiaTestConan(ConanFile):
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
        # Run test binary directly instead of CTest to avoid CTest exit code issues
        exe = os.path.join(self.cpp.build.bindirs[0], "test_cdparanoia")
        self.run(f'"{exe}"', env="conanrun")
