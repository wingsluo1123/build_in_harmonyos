#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace B3Sum, b3sum, 1.8.4, 基于 BLAKE3 哈希算法的命令行工具，使用 NEON SIMD 加速, Apache-2.0, https://github.com/BLAKE3-team/BLAKE3
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class B3SumConan(ConanFile):
    name = "b3sum"
    version = "1.8.4"
    description = "基于 BLAKE3 哈希算法的命令行工具，使用 NEON SIMD 加速"
    license = "Apache-2.0"
    homepage = "https://github.com/BLAKE3-team/BLAKE3"
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
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["BLAKE3_SIMD_TYPE"] = "neon-intrinsics"
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
        self.cpp_info.libs = ["b3sum"]
