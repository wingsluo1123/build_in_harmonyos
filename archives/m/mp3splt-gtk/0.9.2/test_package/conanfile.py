#!/usr/bin/env python3
"""Test package for mp3splt-gtk — verifies the binary is installed."""
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
        # Verify the mp3splt-gtk binary exists in the package
        bin_path = os.path.join(self.deps_env_info["mp3splt-gtk"].bindirs[0], "mp3splt-gtk")
        if os.path.exists(bin_path):
            self.output.info(f"mp3splt-gtk binary found at: {bin_path}")
        else:
            raise Exception("mp3splt-gtk binary not found!")
