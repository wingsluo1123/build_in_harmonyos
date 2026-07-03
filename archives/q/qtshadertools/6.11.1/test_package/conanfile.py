#!/usr/bin/env python3
"""Conan test_package — qtshadertools 6.11.1

L1 test: verify the conan package can be found and configured via CMake.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QtshadertoolsTestConan(ConanFile):
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
        # Explicit self.run() for CI L0d gate compliance
        self.run(os.path.join(self.cpp.build.bindir, "test_qtshadertools"), env="conanrun")
