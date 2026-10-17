#!/usr/bin/env python3
"""Installed-package consumer tests; independent of upstream build outputs."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SgbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="build/installed")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.cache_variables["SGB_DATA_DIRECTORY"] = os.path.join(
            self.dependencies["sgb"].package_folder, "share", "sgb")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        self.run("ctest --output-on-failure --parallel 1", env="conanrun")
