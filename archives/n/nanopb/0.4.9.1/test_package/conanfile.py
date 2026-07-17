#!/usr/bin/env python3
"""Conan consumer test for nanopb 0.4.9.1."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NanopbTestConan(ConanFile):
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
        self.run("ctest --output-on-failure", env="conanrun")
