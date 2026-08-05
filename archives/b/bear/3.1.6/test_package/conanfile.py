#!/usr/bin/env python3
"""Conan test_package for bear — verifies the bear binary works.

Bear is a command-line tool (application), not a library.
This test verifies the binary runs and produces output.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BearTestConan(ConanFile):
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
        # Run bear --version to verify the binary is functional
        # conanrun env sets up PATH to include bear's bin directory
        self.run("bear --version", env="conanrun")
