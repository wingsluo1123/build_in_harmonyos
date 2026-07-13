#!/usr/bin/env python3
"""Conan recipe — libsais 2.10.4 (CMake).

libsais: fast linear-time suffix array construction library.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibsaisConan(ConanFile):
    name = "libsais"
    version = "2.10.4"
    description = "libsais - fast linear-time construction of suffix array, LCP, BWT based on induced sorting"
    license = "MIT"
    homepage = "https://github.com/IlyaGrebnov/libsais"
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
        tc.variables["LIBSAIS_BUILD_SHARED_LIB"] = "OFF"
        # E092: CMake doesn't recognize HarmonyOS, force Linux platform
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        self.cpp_info.libs = ["libsais"]
