#!/usr/bin/env python3
"""Conan test_package for talloc 2.4.2 — L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
File location: archives/t/talloc/2.4.2/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TallocTestConan(ConanFile):
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
        # Run the test binary directly to validate talloc API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_talloc")
        self.run(test_bin, env="conanrun")
