#!/usr/bin/env python3
"""Conan recipe for libuecc 7 — CMake-based ECC library.

libuecc is a very small Elliptic Curve Cryptography library.
Build system: CMake (cmake_minimum_required 2.6, needs policy compat).
R26: Static linking enabled via BUILD_SHARED_LIBS=OFF.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibueccConan(ConanFile):
    name = "libuecc"
    version = "7.0"  # Conan requires version >= 2 chars; upstream is "7"
    description = "Very small Elliptic Curve Cryptography library"
    license = "MIT"
    homepage = "https://git.universe-factory.net/fastd/libuecc"
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
        # R26: Static linking — build static library only
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Compatibility: CMake 4.x removed support for < 3.5
        # Must be cache variable (passed as -D on cmdline, before toolchain load)
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
        self.cpp_info.libs = ["uecc"]
        # Headers installed at include/libuecc-7/libuecc/ecc.h
        self.cpp_info.includedirs = ["include/libuecc-7"]
