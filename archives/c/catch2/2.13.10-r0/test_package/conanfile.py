#!/usr/bin/env python3
"""Conan test_package recipe — catch2 2.13.10-r0 (CMake)"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os


class Catch2TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = ()

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindir, "test_catch2"), env="conanrun")
