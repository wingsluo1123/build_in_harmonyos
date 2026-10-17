#!/usr/bin/env python3
"""Conan test_package for libidn 1.42."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibidnTestConan(ConanFile):
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
        import glob
        bindir = self.build_folder
        candidates = glob.glob(os.path.join(bindir, "**", "test_libidn*"), recursive=True)
        candidates = [c for c in candidates if os.access(c, os.X_OK) and not c.endswith(".cmake")]
        if not candidates:
            raise Exception("test binary not found")
        self.run(candidates[0])
