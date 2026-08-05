#!/usr/bin/env python3
"""Conan test_package for Bear — L1 official test.

Bear is a command-line tool. The test runs the `bear` binary
to verify it was correctly built and installed.
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
        # R34: Test must actually use the tested package
        # Bear is a CLI tool, verify it runs and reports version
        self.run("bear --version", env="conanrun")
