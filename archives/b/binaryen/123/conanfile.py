#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Binaryen, binaryen, 123, binaryen 123, MIT,
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BinaryenConan(ConanFile):
    name = "binaryen"
    version = "123"
    description = "binaryen 123"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        pass  # cmake is available on the system

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
        tc.variables["BUILD_STATIC_LIB"] = "ON"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_C_COMPILER"] = "/data/service/hnp/bin/clang"
        tc.variables["CMAKE_CXX_COMPILER"] = "/data/service/hnp/bin/clang++"
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
        self.cpp_info.libs = ["binaryen"]
