#!/usr/bin/env python3
"""test_package for ecdsautils — L1 consumer test (conan create runs it)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EcdsautilsTestConan(ConanFile):
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
        # Run the built consumer binary directly so its exit code decides the
        # verdict (an explicit self.run() is required by the local CI gate).
        # Single-config generators drop the executable at the build folder root;
        # fall back to the multi-config layout just in case.
        candidates = [
            os.path.join(self.build_folder, "test_ecdsautils"),
            os.path.join(self.build_folder, "Release", "test_ecdsautils"),
        ]
        exe = next((c for c in candidates if os.path.exists(c)), candidates[0])
        self.run(exe, env="conanrun")
