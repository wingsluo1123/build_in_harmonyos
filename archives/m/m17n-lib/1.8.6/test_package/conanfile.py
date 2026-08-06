#!/usr/bin/env python3
"""Conan test_package — m17n-lib 1.8.6

CI runs this automatically via `conan create` (which invokes test_package).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class M17nLibTestConan(ConanFile):
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
