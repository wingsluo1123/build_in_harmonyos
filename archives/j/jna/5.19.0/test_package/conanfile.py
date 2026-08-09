#!/usr/bin/env python3
"""Conan test_package for JNA native library.

Tests that libjnidispatch.so can be loaded via dlopen and that
key JNI function exports are present. This is a smoke test that
verifies the native library is valid without requiring a JVM.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JnaTestConan(ConanFile):
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
        # Run the test binary directly to verify libjnidispatch.so exports
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_jna"), env="conanrun")
