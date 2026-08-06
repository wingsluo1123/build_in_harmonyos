#!/usr/bin/env python3
"""Conan test_package for libsodium — verifies library API works.

R34: Test substantively depends on the libsodium library.
Calls sodium_init() and sodium_library_version_string() to verify linkage.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsodiumTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        cmake = CMake(self)
        cmake.test()
        # Also run the binary directly for L0d compliance
        self.run(os.path.join(self.test_build_folder, "test_libsodium"), env="conanrun")
