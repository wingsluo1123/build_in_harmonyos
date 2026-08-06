#!/usr/bin/env python3
"""Conan test_package for dvgrab — verifies the dvgrab binary works.

R34: Test must substantively depend on the tested package.
dvgrab is a command-line tool, so we execute its binary with --version.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DvgrabTestConan(ConanFile):
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
        # R34: Execute the dvgrab binary to verify it works
        # dvgrab --version prints "dvgrab 3.5.2" and exits 0
        self.run("dvgrab --version", env="conanrun")
