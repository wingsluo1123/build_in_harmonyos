#!/usr/bin/env python3
"""Conan test_package — slang 2.3.3 L1 test.

Tests that the slang library can be linked against and its API
functions (SLang_init_all, SLang_Version, etc.) work correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SlangTestConan(ConanFile):
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
        # Run the test binary directly with the conanrun environment,
        # which sets LD_LIBRARY_PATH to find libslang.so
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_slang")
        self.run(test_bin, env="conanrun")
