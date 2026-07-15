#!/usr/bin/env python3
"""Conan test_package for spim — verifies the spim binary works.

Uses CMake to build a test program that invokes the spim binary
with a simple MIPS assembly program (test_hello.s).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SpimTestConan(ConanFile):
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
