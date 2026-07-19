#!/usr/bin/env python3
"""Conan test_package — lv 4.51-10.1"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LvTestConan(ConanFile):
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
        self.run("which lv", env="conanrun")
        self.run("lv /dev/null", env="conanrun")
