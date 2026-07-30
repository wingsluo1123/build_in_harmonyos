#!/usr/bin/env python3
"""Conan test_package for harfbuzz 14.2.0.

Tests that the harfbuzz library is properly built and linked,
including graphite2 shaper support.

R34: test must substantially depend on the tested package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HarfbuzzTestConan(ConanFile):
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
        # R34: run the test binary which calls harfbuzz API
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_harfbuzz"), env="conanrun")
