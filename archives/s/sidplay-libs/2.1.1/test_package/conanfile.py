#!/usr/bin/env python3
"""Conan test_package — sidplay-libs 2.1.1.

Consumes the packaged libraries (libsidplay2, libsidutils) via C++ API:
- Construct a sidplay2 engine and inspect its config/info (real API call).
- Construct a SidTune object and check identifier API (libsidutils).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class SidplaylibsTestConan(ConanFile):
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
        if not cross_building(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_sidplay-libs"), env="conanrun")
