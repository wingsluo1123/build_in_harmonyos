#!/usr/bin/env python3
"""Conan test_package for apitrace 14.0 — verifies the apitrace CLI tool works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ApitraceTestConan(ConanFile):
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
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_apitrace')}", env="conanrun")
