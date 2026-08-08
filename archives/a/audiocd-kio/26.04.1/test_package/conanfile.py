#!/usr/bin/env python3
"""Conan test_package for audiocd-kio 26.04.1.

Verifies that the audiocdplugins library can be found and linked.
The test links against audiocdplugins and checks that the library
exports the expected symbols.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AudiocdKioTestConan(ConanFile):
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
        # Run the test binary to verify linking succeeds
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_audiocd_kio"), env="conanrun")
