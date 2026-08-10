#!/usr/bin/env python3
"""Conan test_package for libgpiod 2.0 — verifies the C API is functional.

Calls gpiod_api_version() to confirm the library is correctly linked.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgpiodTestConan(ConanFile):
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
        # R34: directly execute the test binary to verify library linkage
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libgpiod')}", env="conanrun")
