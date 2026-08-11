#!/usr/bin/env python3
"""Conan test_package for wcslib 8.4.

Builds a test program that calls the WCSLIB prj (projection) API:
  prjini() -> prjset() -> prjx2s() -> prjs2x() -> verify closure.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WcslibTestConan(ConanFile):
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
