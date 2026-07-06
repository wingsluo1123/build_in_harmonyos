#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Blosc, blosc, 1.21.6, 高性能块压缩库，支持多线程和多种压缩算法, BSD-3-Clause, https://github.com/Blosc/c-blosc
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BloscConan(ConanFile):
    name = "blosc"
    version = "1.21.6"
    description = "高性能块压缩库，支持多线程和多种压缩算法"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Blosc/c-blosc"
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
        tc.variables["PREFER_EXTERNAL_ZSTD"] = "ON"
        tc.variables["DEACTIVATE_SNAPPY"] = "ON"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_FUZZERS"] = "OFF"
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["blosc"]
