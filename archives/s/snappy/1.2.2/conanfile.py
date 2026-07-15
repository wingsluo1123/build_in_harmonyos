#!/usr/bin/env python3
"""Conan recipe for snappy 1.2.2 — CMake project.

Snappy is a fast compression/decompression library by Google.
Build system: CMake (no autotools configure script).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SnappyConan(ConanFile):
    name = "snappy"
    version = "1.2.2"
    description = "Fast compression/decompression library by Google"
    license = "BSD-3-Clause"
    homepage = "https://google.github.io/snappy/"
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
        # Disable tests/benchmarks (third_party submodules not in tarball)
        tc.variables["SNAPPY_BUILD_TESTS"] = "OFF"
        tc.variables["SNAPPY_BUILD_BENCHMARKS"] = "OFF"
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
        self.cpp_info.libs = ["snappy"]
