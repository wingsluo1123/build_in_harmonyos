#!/usr/bin/env python3
"""Conan recipe for misa77 0.6.0 (CMake, C++20).
Upstream builds via CMake; no external third-party deps. Includes a CLI tool
(`misa`) and a static library (`libmisa77.a`).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class Misa77Conan(ConanFile):
    name = "misa77"
    version = "0.6.0"
    description = "misa77 - a fast-decompression LZ77-style compressor"
    license = "MIT"
    homepage = "https://github.com/welcome-to-the-sunny-side/misa77"
    url = "https://github.com/welcome-to-the-sunny-side/misa77"

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
        tc.variables["MISA77_BUILD_TESTS"] = "OFF"  # upstream tests run separately
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream CMakeLists has no install() rules; collect artifacts manually.
        copy(self, "misa77.h", src=os.path.join(self.source_folder, "include", "misa77"),
             dst=os.path.join(self.package_folder, "include", "misa77"))
        copy(self, "experimental.h", src=os.path.join(self.source_folder, "include", "misa77"),
             dst=os.path.join(self.package_folder, "include", "misa77"))
        copy(self, "libmisa77.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "misa", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["misa77"]
        self.cpp_info.bindirs = ["bin"]