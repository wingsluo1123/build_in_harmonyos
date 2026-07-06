#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Dfc, dfc, 3.1.1, Report file system space usage information with colors and graphs, BSD-3-Clause, https://github.com/rolinh/dfc
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DfcConan(ConanFile):
    name = "dfc"
    version = "3.1.1"
    description = "Report file system space usage information with colors and graphs"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rolinh/dfc"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["NLS_ENABLED"] = "false"
        # CMAKE_POLICY_VERSION_MINIMUM as cache var (needed before cmake_minimum_required)
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
        # dfc is a standalone executable, no shared libraries
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
