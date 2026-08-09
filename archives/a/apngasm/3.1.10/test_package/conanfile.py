#!/usr/bin/env python3
"""Conan test_package — apngasm 3.1.10

This test creates an APNGAsm object and calls version() to verify
the library is correctly linked and functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ApngasmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("libpng", "cmake_file_name", "PNG")
        deps.set_property("libpng", "cmake_target_name", "PNG::PNG")
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Also run the binary directly to verify functionality
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_apngasm")
        self.run(test_bin, env="conanrun")
