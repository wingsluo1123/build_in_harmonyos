#!/usr/bin/env python3
"""Conan test_package for irssi — verifies the irssi binary works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IrssiTestConan(ConanFile):
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
        # Run the irssi binary to verify it works
        irssi_bin = os.path.join(self.dependencies["irssi"].cpp_info.bindirs[0], "irssi")
        self.run(f'"{irssi_bin}" --version', env="conanrun")
