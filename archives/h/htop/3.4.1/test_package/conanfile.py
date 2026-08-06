#!/usr/bin/env python3
"""Conan test_package for htop 3.4.1 — L1 test.

htop is a command-line application. The test runs `htop --version`
to verify the binary is functional and linked correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HtopTestConan(ConanFile):
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
        # R34: test must actually exercise the tested package's binary
        # Run htop --version to verify the binary works
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_htop')}", env="conanrun")
