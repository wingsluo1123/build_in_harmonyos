#!/usr/bin/env python3
"""Conan test_package — lhasa 0.6.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LhasaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
        lha_bin = os.path.join(self.dependencies["lhasa"].package_folder, "bin", "lha")
        self.run(f'"{lha_bin}" || test $? -eq 255', env="conanrun")
