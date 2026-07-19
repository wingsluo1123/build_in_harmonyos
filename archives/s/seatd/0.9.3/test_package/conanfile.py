#!/usr/bin/env python3
"""Conan test_package - seatd 0.9.3 (L1 test).

Verifies that the libseat header is available after installation.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SeatdTestConan(ConanFile):
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
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_seatd"),
            env="conanrun",
        )
