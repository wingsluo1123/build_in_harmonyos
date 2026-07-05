#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Blend2D, blend2d, 0.21.2, High-performance 2D vector graphics engine written in C++, BSD-3-Clause, https://github.com/blend2d/blend2d
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Blend2DConan(ConanFile):
    name = "blend2d"
    version = "0.21.2"
    description = "High-performance 2D vector graphics engine written in C++"
    license = "BSD-3-Clause"
    homepage = "https://github.com/blend2d/blend2d"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["blend2d"]
