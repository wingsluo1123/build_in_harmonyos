#!/usr/bin/env python3
"""Conan recipe — matio 1.5.26 (CMake build).

Adapted per matio 1.5.23 historical notes: CMake build on HarmonyOS
(autotools has temp-dir permission issues), static library, MAT73/HDF5
disabled (no external deps).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MatioConan(ConanFile):
    name = "matio"
    version = "1.5.26"
    description = "MATIO is a C library for reading and writing MATLAB MAT files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/tbeu/matio"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # HarmonyOS adaptation per 1.5.23 history: disable MAT73/HDF5/zlib
        # to keep zero external dependencies; static lib avoids LLVM linker
        # GNU-style symbol file issues.
        tc.variables["MATIO_MAT73"] = "OFF"
        tc.variables["MATIO_WITH_HDF5"] = "OFF"
        tc.variables["MATIO_WITH_ZLIB"] = "OFF"
        tc.variables["MATIO_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["MATIO_USE_CONAN"] = "OFF"
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
        self.cpp_info.libs = ["matio"]