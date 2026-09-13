#!/usr/bin/env python3
"""Consumer tests for the packaged nsnake executable."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NsnakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

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
        executable = os.path.join(self.dependencies["nsnake"].package_folder, "bin", "nsnake")
        self.run(f"{executable} --version", env="conanrun")
        self.run(f"{executable} --help", env="conanrun")
