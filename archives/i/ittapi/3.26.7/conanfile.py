#!/usr/bin/env python3
"""Conan recipe — ittapi 3.26.7 (CMake build system).

Intel Instrumentation and Tracing Technology (ITT) API.
Static library for performance profiling on Intel platforms.

R26: Static linking enforced via BUILD_SHARED_LIBS=OFF.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IttapiConan(ConanFile):
    name = "ittapi"
    version = "3.26.7"
    description = "Intel Instrumentation and Tracing Technology (ITT) API - static profiling library"
    license = "GPL-2.0-only OR BSD-3-Clause"
    homepage = "https://github.com/intel/ittapi"
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
        # R26: Terminal tools must be statically linked
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
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
        self.cpp_info.libs = ["ittnotify"]
        self.cpp_info.system_libs = ["dl"]
