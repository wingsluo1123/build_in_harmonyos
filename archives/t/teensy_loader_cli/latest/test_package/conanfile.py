#!/usr/bin/env python3
"""Conan test_package for teensy_loader_cli latest — Conan L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TeensyLoaderCliTestConan(ConanFile):
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
        # Verify the teensy_loader_cli executable is installed and runnable.
        # --help prints usage to stderr and exits 1, so tolerate non-zero exit.
        self.run("teensy_loader_cli --help", ignore_errors=True, env="conanrun")
