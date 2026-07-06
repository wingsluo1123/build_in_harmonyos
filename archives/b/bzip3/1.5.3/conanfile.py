#!/usr/bin/env python3
"""Conan recipe — bzip3 1.5.3 (CMake build).

bzip3 is a next-generation compression library and tool.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Bzip3Conan(ConanFile):
    name = "bzip3"
    version = "1.5.3"
    description = "Next-generation bzip compression tool with modern algorithms"
    license = "LGPL-3.0"
    homepage = "https://github.com/kspalaiologos/bzip3"
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
        # R26: Static build for system isolation
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BZIP3_ENABLE_PTHREAD"] = "ON"
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
        self.cpp_info.libs = ["bzip3"]
