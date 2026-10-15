#!/usr/bin/env python3
"""Conan test_package — plib 1.8.5 consumer test.

Builds a small program against the packaged plib static libraries and runs it.
Exercises the sg (3D math) core module with real numeric assertions.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("can_run() is False - skipping plib consumer test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_plib"), env="conanrun")
