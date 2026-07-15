#!/usr/bin/env python3
"""Conan recipe for jansson 2.15.0.

Jansson is a C library for encoding, decoding and manipulating JSON data.
It uses a straightforward API and supports UTF-8 encoded JSON.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class JanssonConan(ConanFile):
    name = "jansson"
    version = "2.15.0"
    description = "C library for encoding, decoding and manipulating JSON data"
    license = "MIT"
    homepage = "https://github.com/akheron/jansson"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Build static library by default for reliable deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
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
        self.cpp_info.libs = ["jansson"]
