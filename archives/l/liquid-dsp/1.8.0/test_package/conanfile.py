#!/usr/bin/env python3
"""Conan test_package — liquid-dsp v1.8.0

L1 consumer test: verify liquid_libversion() returns correct version.
R34: test_package must substantially exercise the tested package's API.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LiquiddspTestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_liquid-dsp")
            self.run(bin_path, env="conanrun")
