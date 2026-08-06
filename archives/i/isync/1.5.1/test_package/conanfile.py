#!/usr/bin/env python3
"""Conan test_package for isync 1.5.1.

isync is a command-line tool (mbsync), not a library.
This test builds a C test program that runs mbsync --version
to verify the installed binary is functional (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IsyncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
        # R34: Explicitly run the test binary to verify mbsync is functional
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_isync"), env="conanrun")
