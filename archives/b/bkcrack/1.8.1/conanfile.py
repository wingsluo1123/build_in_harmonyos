#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Bkcrack, bkcrack, 1.8.1, Crack legacy zip encryption with Biham and Kocher's known plaintext attack, Zlib, https://github.com/kimci86/bkcrack
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BkcrackConan(ConanFile):
    name = "bkcrack"
    version = "1.8.1"
    description = "Crack legacy zip encryption with Biham and Kocher's known plaintext attack"
    license = "Zlib"
    homepage = "https://github.com/kimci86/bkcrack"
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
        tc.variables["CMAKE_INSTALL_PREFIX"] = "$DEFAULT_PREFIX"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["BKCRACK_BUILD_TESTING"] = "ON"
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
        self.cpp_info.libs = ["bkcrack"]
