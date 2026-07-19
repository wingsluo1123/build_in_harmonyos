#!/usr/bin/env python3
"""Conan recipe — xsimd 13.0.0 (CMake, header-only).

xsimd is a C++ header-only library providing SIMD intrinsics wrappers.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class XsimdConan(ConanFile):
    name = "xsimd"
    version = "13.0.0"
    description = "C++ wrappers for SIMD intrinsics - header-only library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/xtensor-stack/xsimd"
    url = ""  # CI fills this

    package_type = "header-library"

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
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
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
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "xsimd")
        self.cpp_info.set_property("cmake_target_name", "xsimd::xsimd")
