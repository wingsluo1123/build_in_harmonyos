#!/usr/bin/env python3
"""Conan test_package for aws-c-http 0.10.14.

Verifies the library links and basic HTTP library API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwschttpTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_aws-c-http"), env="conanrun")
