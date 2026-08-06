#!/usr/bin/env python3
"""Test package for mp3splt-gtk — verifies the binary is installed and runnable."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Mp3SpltGtkTestConan(ConanFile):
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
        # Verify the mp3splt-gtk binary is installed
        bin_dir = self.dependencies["mp3splt-gtk"].cpp_info.bindirs[0]
        bin_path = os.path.join(bin_dir, "mp3splt-gtk")
        assert os.path.exists(bin_path), f"mp3splt-gtk binary not found at {bin_path}"
        self.output.info(f"mp3splt-gtk binary verified at: {bin_path}")
