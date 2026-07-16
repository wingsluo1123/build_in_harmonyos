#!/usr/bin/env python3
"""Conan test_package — flake 0.11 L1 test"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FlakeTestConan(ConanFile):
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
        # Explicit binary smoke test (R34: must execute the tested package's binary)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_flake")
        self.run(exe, env="conanrun")
