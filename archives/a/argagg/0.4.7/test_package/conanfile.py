#!/usr/bin/env python3
"""Conan test_package for argagg — Conan L1 official test.

Compiles test.cpp against the argagg header-only library and runs it.
Uses Conan's CMakeToolchain for proper cross-compilation support.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ArgaggTestConan(ConanFile):
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
