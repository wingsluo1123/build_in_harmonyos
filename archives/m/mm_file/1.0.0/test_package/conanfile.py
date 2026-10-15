#!/usr/bin/env python3
"""Conan test_package — mm_file 1.0.0 (header-only memory-mapped files).

L1 consumer test: includes the mm_file header and exercises the real
API (file_sink write / file_source read / advice), verifying round-trip
data integrity. Not an empty-shell test (R34/PF3).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MmFileTestConan(ConanFile):
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
        # run the consumer binary directly as well
        self.run("./test_mm_file", env="conanrun")
