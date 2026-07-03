#!/usr/bin/env python3
"""Conan test_package — smartmontools 7.5.

L1 test: verify smartctl binary is installed and runs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SmartmontoolsTestConan(ConanFile):
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
        # Run the CMake test
        cmake = CMake(self)
        cmake.test()
        # Also verify smartctl binary works
        smartctl = os.path.join(self.dependencies["smartmontools"].package_folder, "bin", "smartctl")
        self.run(f"{smartctl} --version", env="conanrun")
