#!/usr/bin/env python3
"""Conan test_package for graphite2 1.3.14.

R34: This test substantively depends on the graphite2 package by
calling gr_engine_version() to verify the library is correctly
linked and functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Graphite2TestConan(ConanFile):
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
        # R34: Run the test binary directly to verify substantive dependency
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_graphite2")
        self.run(test_exe, env="conanrun")
