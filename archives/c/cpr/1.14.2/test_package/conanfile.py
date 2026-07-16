#!/usr/bin/env python3
"""Conan test_package for cpr 1.14.2 — verifies the library compiles and links correctly.

Builds test_cpr.cpp and runs the resulting binary to confirm cpr headers
and the static library are usable from a consumer project.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CprTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindir, "test_cpr")
        self.run(bin_path, env="conanrun")