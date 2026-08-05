#!/usr/bin/env python3
"""Conan test_package — apr 1.7.6 L1 test.

Tests APR API: apr_initialize, apr_pool_create, apr_version_string,
apr_pool_destroy, apr_terminate.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AprTestConan(ConanFile):
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
        # Explicitly run the test binary for CI gate verification
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_apr"), env="conanrun")
