#!/usr/bin/env python3
"""Conan test_package for perf 6.6.9 — verifies the perf binary is built and packaged.

This test runs `perf --version` to verify the binary is functional.
On OHOS, the binary may need signing before it can execute.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PerfTestConan(ConanFile):
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
        # Run the test binary that checks perf
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_perf')}", env="conanrun")
