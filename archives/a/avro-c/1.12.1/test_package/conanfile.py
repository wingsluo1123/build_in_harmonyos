#!/usr/bin/env python3
"""Conan test_package — avro-c 1.12.1 L1 test.

Verifies avro C API: schema parsing, record creation, serialization,
deserialization, and value verification.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AvroCTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_avro"), env="conanrun")
