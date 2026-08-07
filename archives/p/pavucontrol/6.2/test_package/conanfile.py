#!/usr/bin/env python3
"""Conan test_package — pavucontrol 6.2

L1 test: verifies the pavucontrol binary is installed and can report its version.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PavucontrolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary that calls pavucontrol --version
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_pavucontrol")
        self.run(cmd, env="conanrun")
