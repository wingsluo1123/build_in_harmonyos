#!/usr/bin/env python3
"""Conan test_package for cdparanoia 10.2 — verifies library links correctly."""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CdparanoiaTestConan(ConanFile):
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
        # Find the test binary and run it directly (CI gate requires self.run())
        exes = glob.glob(
            os.path.join(self.build_folder, "**", "test_cdparanoia*"),
            recursive=True,
        )
        if not exes:
            exes = [os.path.join(self.build_folder, "test_cdparanoia")]
        self.run(f'"{exes[0]}"', env="conanrun")
