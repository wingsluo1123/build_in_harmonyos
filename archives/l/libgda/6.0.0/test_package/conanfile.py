#!/usr/bin/env python3
"""Conan test_package for libgda 6.0.0.

Verifies that the libgda library can be linked and its API called.
Uses CMake to build the test program, then runs it directly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgdaTestConan(ConanFile):
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
        # Run the test binary directly to verify the library works
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libgda")
        self.run(test_binary, env="conanrun")
